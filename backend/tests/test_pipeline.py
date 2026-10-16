from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from sqlalchemy import func, select
from app.clock import window
from app.feeds import parse_feed
from app.jobs import claim_next, enqueue, ensure_due, recover_interrupted
from app.models import DailyReport, JobRun, News, NewsAnalysis, ReportItem, Source
from app.pipeline import execute_job, persist_news
from app.reports import report_dict
from conftest import DAY, entry, rss, eight_feeds


def run_report(env,fetcher=eight_feeds):
    settings,factory=env
    job=enqueue(factory,DAY)
    assert claim_next(factory)==job["id"]
    execute_job(factory,settings,job["id"],fetcher)
    return job["id"]


def test_concurrent_enqueue_has_one_active_job(env):
    with ThreadPoolExecutor(8) as pool:
        jobs=list(pool.map(lambda _:enqueue(env[1],DAY),range(16)))
    assert len({job["id"] for job in jobs})==1
    with env[1]() as session:
        assert session.scalar(select(func.count()).select_from(JobRun))==1


def test_eight_sections_and_idempotent_rerun(env):
    run_report(env)
    run_report(env)
    with env[1]() as session:
        assert session.scalar(select(func.count()).select_from(DailyReport))==1
        report=session.scalar(select(DailyReport))
        result=report_dict(session,report)
        assert result["total"]==8 and report.status=="ready"
        assert set(report.coverage.values())=={1}
        assert len(result["items"])==8
        assert all(i["analysis_status"]=="extractive" for i in result["items"])


def test_duplicates_across_sources_merged(env):
    run_report(env,lambda source,settings:rss([entry()]))
    with env[1]() as session:
        assert sum(session.scalar(select(DailyReport)).coverage.values())==1


def test_partial_source_failure_is_visible(env):
    def fetcher(source,settings):
        if source.id=="china-finance": raise ValueError("fixture failure")
        return eight_feeds(source,settings)
    run_report(env,fetcher)
    with env[1]() as session:
        report=session.scalar(select(DailyReport))
        assert report.status=="partial" and sum(report.coverage.values())==7
        assert sum(r["status"]=="error" for r in report.source_results)==1


def test_total_failure_preserves_published_report(env):
    run_report(env)
    with env[1]() as session:
        original=report_dict(session,session.scalar(select(DailyReport)))
    def broken(*args): raise ValueError("all broken")
    job_id=run_report(env,broken)
    with env[1]() as session:
        assert report_dict(session,session.scalar(select(DailyReport)))==original
        assert session.get(JobRun,job_id).status=="failed"
        assert session.get(JobRun,job_id).active_slot is None


def test_empty_feed_does_not_fabricate_items(env):
    run_report(env,lambda *_:rss([]))
    with env[1]() as session:
        report=session.scalar(select(DailyReport))
        assert report.status=="empty" and sum(report.coverage.values())==0


def test_cache_keeps_articles_no_longer_present_in_rss(env,source):
    item=parse_feed(rss([entry()]),source,*window(DAY,env[0]))[0][0]
    persist_news(env[1],item)
    run_report(env,lambda *_:rss([]))
    with env[1]() as session:
        assert sum(session.scalar(select(DailyReport)).coverage.values())==1


def test_published_snapshot_does_not_change_when_original_changes(env):
    run_report(env)
    with env[1].begin() as session:
        item=session.scalar(select(ReportItem))
        original=item.snapshot["original_title"]
        session.get(News,item.news_id).title="changed after publication"
    with env[1]() as session:
        assert session.scalar(select(ReportItem)).snapshot["original_title"]==original


def test_recovery_releases_crashed_job(env):
    job=enqueue(env[1],DAY);claim_next(env[1]);recover_interrupted(env[1])
    with env[1]() as session:
        assert session.get(JobRun,job["id"]).status=="failed"
    assert enqueue(env[1],DAY)["id"]!=job["id"]


def test_catchup_only_once_without_infinite_failed_retries(env,monkeypatch):
    monkeypatch.setattr("app.jobs.due_today",lambda settings:DAY)
    ensure_due(env[1],env[0]);ensure_due(env[1],env[0])
    with env[1]() as session:
        assert session.scalar(select(func.count()).select_from(JobRun))==1
