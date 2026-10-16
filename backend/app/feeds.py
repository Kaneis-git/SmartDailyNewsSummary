import hashlib
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import feedparser
import httpx

MAX_FEED_BYTES = 2_000_000


class TextOnly(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        elif tag in ("br", "p", "div", "li"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def clean_html(text):
    parser = TextOnly()
    parser.feed(str(text or ""))
    return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def canonical_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("无效新闻链接")
    pairs = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid", "ocid")]
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", urlencode(sorted(pairs)), ""))


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def title_key(title):
    return re.sub(r"[\W_]+", "", title.casefold())


def parse_published(raw):
    if not raw:
        return None
    try:
        value = parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if value.tzinfo is None:
        return None
    return value.astimezone(UTC).replace(tzinfo=None)


def parse_feed(data: bytes, source, start, end):
    if len(data) > MAX_FEED_BYTES or b"<!ENTITY" in data.upper() or b"<!DOCTYPE" in data.upper():
        raise ValueError("Feed 格式或大小不符合要求")
    parsed = feedparser.parse(data)
    if not parsed.version:
        raise ValueError("响应不是有效的 RSS/Atom")
    items, skipped = [], 0
    for entry in parsed.entries[:200]:
        published = parse_published(entry.get("published"))
        title = clean_html(entry.get("title"))[:500]
        if not published or not start <= published < end or not title:
            skipped += 1
            continue
        try:
            url = canonical_url(entry.get("link", ""))
        except ValueError:
            skipped += 1
            continue
        # Only use feed-provided excerpts; never scrape the linked article.
        excerpt = clean_html(entry.get("summary", ""))[:6000]
        items.append({"title": title, "url": url, "url_hash": digest(url),
                      "text_excerpt": excerpt, "content_hash": digest(title + "\n" + excerpt),
                      "published_at": published, "source_id": source.id,
                      "source_name": source.name, "region_hint": source.region_hint,
                      "category_hint": source.category_hint})
    return items, {"seen": len(parsed.entries[:200]), "accepted": len(items), "skipped": skipped}


def fetch_feed(source, settings):
    with httpx.Client(timeout=settings.feed_timeout, follow_redirects=False,
                      headers={"User-Agent": "AI-Daily-News-Assistant/0.1 (personal RSS reader)"}) as client:
        with client.stream("GET", source.feed_url) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > MAX_FEED_BYTES:
                    raise ValueError("Feed 响应过大")
            return bytes(data)


def source_error(exc):
    if isinstance(exc, httpx.HTTPStatusError):
        return f"HTTP {exc.response.status_code}；请检查来源地址或服务状态"
    if isinstance(exc, httpx.TimeoutException):
        return "连接超时；请检查本机网络或更换来源"
    if isinstance(exc, httpx.RequestError):
        return "无法连接来源；请检查网络和 DNS"
    return "数据格式无效；请检查 RSS 地址、发布时间和响应大小"
