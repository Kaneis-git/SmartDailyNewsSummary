import logging
from collections import defaultdict
from sqlalchemy import delete, select
from ai_service.analyzer import analyze
from ai_service.classifier import classify
from ai_service.prompt import PROMPT_VERSION
from ai_service.taxonomy import CATEGORIES, REGIONS
from .clock import iso, utcnow, window
from .feeds import digest, fetch_feed, parse_feed, source_error, title_key
from .models import DailyReport, JobRun, News, NewsAnalysis, ReportItem, Source

from .notifications import queue_report_notifications

logger = logging.getLogger(__name__)


def progress(factory, job_id, message, source_results=None):
    with factory.begin() as session:
        job = session.get(JobRun, job_id)
        job.message = message
        if source_results is not None:
            job.source_results = list(source_results)


def persist_news(factory, item):
    with factory.begin() as session:
        row = session.scalar(select(News).where(News.url_hash == item["url_hash"]))
        values = {key: item[key] for key in ("source_id", "title", "url", "url_hash", "text_excerpt", "content_hash", "published_at")}
        if row is None:
            row = News(**values)
            session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
            row.fetched_at = utcnow()
        session.flush()
        return row.id


def analysis_for(factory, item, news_id, settings):
    model = (settings.ai_model + "@" + digest(settings.ai_base_url)[:12]) if settings.ai_enabled else "extractive-v1"
    with factory() as session:
        old = session.scalar(select(NewsAnalysis).where(NewsAnalysis.news_id == news_id,
            NewsAnalysis.content_hash == item["content_hash"], NewsAnalysis.model == model,
            NewsAnalysis.prompt_version == PROMPT_VERSION))
        if old and old.status == "ai":
            return old.id, old.payload, old.status
        old_id = old.id if old else None
    payload, status = analyze(item, settings)
    with factory.begin() as session:
        row = session.get(NewsAnalysis, old_id) if old_id else NewsAnalysis(
            news_id=news_id, content_hash=item["content_hash"], model=model, prompt_version=PROMPT_VERSION)
        row.payload, row.status = payload, status
        session.add(row)
        session.flush()
        return row.id, payload, status


def generate_report(factory, settings, job_id, fetcher=fetch_feed):
    with factory() as session:
        job = session.get(JobRun, job_id)
        day = job.report_date
        sources = list(session.scalars(select(Source).where(Source.enabled.is_(True)).order_by(Source.id)))
    start, end = window(day, settings)
    candidates, results = [], []
    for source in sources:
        progress(factory, job_id, f"采集 {source.name}", results)
        try:
            items, counts = parse_feed(fetcher(source, settings), source, start, end)
            candidates.extend(items)
            results.append({"id": source.id, "name": source.name, "status": "ok", **counts,
                            "message": "采集成功" if items else "源可读取，本期无符合时间条件的条目"})
        except Exception as exc:
            logger.warning("feed_failure source=%s type=%s", source.id, type(exc).__name__)
            results.append({"id": source.id, "name": source.name, "status": "error", "seen": 0,
                            "accepted": 0, "skipped": 0, "message": source_error(exc)})
    progress(factory, job_id, "筛选与去重", results)
    if not any(result["status"] == "ok" for result in results):
        raise RuntimeError("全部新闻源不可用或未启用；请在数据源页检查，已有日报未改动")
    # RSS often retains only the latest entries. Merge the rolling local cache
    # so stories collected earlier in this 24-hour window remain eligible.
    for item in candidates:
        persist_news(factory, item)
    source_map = {source.id: source for source in sources}
    with factory() as session:
        for news in session.scalars(select(News).where(News.published_at >= start, News.published_at < end)):
            source = source_map.get(news.source_id)
            if source:
                candidates.append({"title": news.title, "url": news.url, "url_hash": news.url_hash,
                    "text_excerpt": news.text_excerpt, "content_hash": news.content_hash,
                    "published_at": news.published_at, "source_id": source.id, "source_name": source.name,
                    "region_hint": source.region_hint, "category_hint": source.category_hint})
    buckets = defaultdict(list)
    seen_urls, seen_titles = set(), set()
    for item in sorted(candidates, key=lambda i: i["published_at"], reverse=True):
        key = title_key(item["title"])
        if item["url_hash"] in seen_urls or key in seen_titles:
            continue
        seen_urls.add(item["url_hash"])
        seen_titles.add(key)
        region, category, importance = classify(item)
        if category in CATEGORIES:
            item["rule_importance"] = importance
            buckets[(region, category)].append(item)
    shortlist = []
    for region in REGIONS:
        for category in CATEGORIES:
            batch = sorted(buckets[(region, category)], key=lambda i: (i["rule_importance"], i["published_at"]), reverse=True)
            shortlist.extend(batch[:settings.max_per_section * settings.candidate_multiplier])
    selected = defaultdict(list)
    for index, item in enumerate(shortlist):
        progress(factory, job_id, f"整理新闻 {index + 1}/{len(shortlist)}", results)
        news_id = persist_news(factory, item)
        analysis_id, payload, status = analysis_for(factory, item, news_id, settings)
        if payload["category"] not in CATEGORIES:
            continue
        snapshot = {"id": news_id, "original_title": item["title"], "title": payload["headline"],
                    "source_name": item["source_name"], "source_id": item["source_id"], "url": item["url"],
                    "published_at": iso(item["published_at"]), "original_excerpt": item["text_excerpt"],
                    "analysis_status": status, "analysis": payload, "report_date": day.isoformat()}
        selected[(payload["region"], payload["category"])].append((news_id, analysis_id, snapshot))
    final, coverage = [], {}
    for region in REGIONS:
        for category in CATEGORIES:
            rows = sorted(selected[(region, category)], key=lambda i: (i[2]["analysis"]["importance"], i[2]["published_at"]), reverse=True)
            rows = rows[:settings.max_per_section]
            coverage[f"{region}.{category}"] = len(rows)
            final.extend(rows)
    status = "empty" if not final else ("partial" if any(r["status"] == "error" for r in results) or not all(coverage.values()) else "ready")
    # A single transaction publishes the complete snapshot and final job state.
    with factory.begin() as session:
        report = session.scalar(select(DailyReport).where(DailyReport.report_date == day))
        if report is None:
            report = DailyReport(report_date=day)
            session.add(report)
        else:
            session.execute(delete(ReportItem).where(ReportItem.report_id == report.id))
        report.window_start, report.window_end, report.generated_at = start, end, utcnow()
        report.status, report.coverage, report.source_results = status, coverage, results
        session.flush()
        for position, (news_id, analysis_id, snapshot) in enumerate(final):
            session.add(ReportItem(report_id=report.id, news_id=news_id, analysis_id=analysis_id,
                position=position, region=snapshot["analysis"]["region"], category=snapshot["analysis"]["category"], snapshot=snapshot))
        job = session.get(JobRun, job_id)
        job.status, job.active_slot, job.finished_at = "succeeded", None, utcnow()
        job.message = f"日报已生成，共 {len(final)} 条新闻" if final else "本期无符合条件的新闻，请检查来源覆盖及时间"
        job.source_results = results
        if final: queue_report_notifications(session, report, settings)


def execute_job(factory, settings, job_id, fetcher=fetch_feed):
    try:
        generate_report(factory, settings, job_id, fetcher)
    except Exception as exc:
        logger.error("job_failed id=%s type=%s", job_id, type(exc).__name__)
        message = str(exc) if isinstance(exc, RuntimeError) else "处理失败，旧日报已保留；请检查 worker 日志后重试"
        with factory.begin() as session:
            job = session.get(JobRun, job_id)
            job.status, job.active_slot, job.finished_at, job.message = "failed", None, utcnow(), message
