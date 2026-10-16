import logging
from datetime import UTC, timedelta
from threading import Lock
from apscheduler.schedulers.blocking import BlockingScheduler
from filelock import FileLock, Timeout
from .clock import utcnow
from .collector import collect_recent
from .config import get_settings
from .db import make_session_factory, sync_sources
from .jobs import claim_next, ensure_due, recover_interrupted
from .models import RuntimeState
from .pipeline import execute_job
from .notifications import dispatch_notifications,recover_notifications


def run_worker():
    settings = get_settings()
    factory = make_session_factory(settings.db_url)
    lock = FileLock(settings.data_dir / ".worker.lock", timeout=0)
    try:
        lock.acquire()
    except Timeout:
        raise SystemExit("已有 worker 使用此数据目录；请只启动一个 worker")
    try:
        sync_sources(factory, settings.sources_file)
        recover_interrupted(factory)
        recover_notifications(factory)
        pipeline_lock = Lock()

        def heartbeat():
            with factory.begin() as session:
                session.merge(RuntimeState(key="worker_heartbeat", value=utcnow().isoformat()))

        def consume():
            if pipeline_lock.acquire(blocking=False):
                try:
                    job_id = claim_next(factory)
                    if job_id:
                        execute_job(factory, settings, job_id)
                finally:
                    pipeline_lock.release()

        def collect():
            if pipeline_lock.acquire(blocking=False):
                try:
                    collect_recent(factory, settings)
                finally:
                    pipeline_lock.release()

        heartbeat()
        ensure_due(factory, settings)
        scheduler = BlockingScheduler(timezone=settings.timezone)
        scheduler.add_job(lambda: dispatch_notifications(factory,settings),"interval",seconds=10,max_instances=1,coalesce=True)
        scheduler.add_job(heartbeat, "interval", seconds=10, max_instances=1, coalesce=True)
        scheduler.add_job(consume, "interval", seconds=2, max_instances=1, coalesce=True)
        # Give a due report priority, then begin rolling capture.
        scheduler.add_job(collect, "interval", minutes=30, next_run_time=utcnow().replace(tzinfo=UTC) + timedelta(seconds=20), max_instances=1, coalesce=True)
        scheduler.add_job(lambda: ensure_due(factory, settings), "cron", hour=settings.report_hour,
                          minute=settings.report_minute, misfire_grace_time=86400, coalesce=True, max_instances=1)
        scheduler.add_job(lambda: ensure_due(factory, settings), "interval", seconds=60, max_instances=1, coalesce=True)
        logging.info("Worker ready; timezone=%s schedule=%02d:%02d", settings.timezone, settings.report_hour, settings.report_minute)
        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown(wait=True)
    finally:
        lock.release()


if __name__ == "__main__":
    run_worker()
