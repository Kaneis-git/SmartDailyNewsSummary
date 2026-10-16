import json
from datetime import UTC, date, datetime
from email.utils import format_datetime
from html import escape
import pytest
from sqlalchemy import select
from app.config import Settings
from app.db import make_session_factory, sync_sources
from app.models import Source

DAY = date(2026, 10, 12)
PUBLISHED = datetime(2026, 10, 11, 20, 0, tzinfo=UTC)


def rss(entries):
    body = "".join(f"<item><title>{escape(e['title'])}</title><link>{escape(e['url'])}</link>"
        + (f"<pubDate>{escape(e['published'])}</pubDate>" if e.get('published') else "")
        + f"<description>{escape(e.get('text', 'This is a fixture excerpt, not real news.'))}</description></item>" for e in entries)
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>Test fixtures</title>{body}</channel></rss>'.encode()


def entry(title="央行调整货币政策", url="https://news.example/story", published=None, text=None):
    return {"title": title, "url": url, "published": published or format_datetime(PUBLISHED),
            "text": text or "测试用例：新闻摘要的内容仅用于验证程序，不是真实新闻，不应用于真实新闻日报。"}


@pytest.fixture
def env(tmp_path):
    configs = [{"id":f"{r}-{c}","name":f"Fixture {r} {c}","feed_url":f"https://feeds.example/{r}/{c}",
                "region_hint":r,"category_hint":c,"enabled":True}
               for r in ("china","international") for c in ("politics","finance","technology","ai")]
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(configs), encoding="utf-8")
    settings = Settings(_env_file=None, data_dir=tmp_path / "data", sources_file=path,
                        ai_base_url="", ai_model="", ai_api_key="", admin_token="")
    factory = make_session_factory(settings.db_url)
    sync_sources(factory, path)
    return settings, factory


@pytest.fixture
def source(env):
    with env[1]() as session:
        return session.scalar(select(Source).where(Source.id=="china-finance"))


def eight_feeds(source, settings):
    titles = {"politics":"Government policy review 政府政策调整", "finance":"Central bank interest rates 央行货币利率调整",
              "technology":"Chip technology 半导体芯片研发", "ai":"人工智能大模型应用发布"}
    return rss([entry(title=titles[source.category_hint]+" "+source.id, url=f"https://news.example/{source.id}")])
