from uuid import uuid4
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from .clock import due_today, iso, utcnow
from .models import JobRun


def job_dict(job):
    return {"id": job.id, "report_date": job.report_date.isoformat(), "status": job.status,
            "message": job.message, "created_at": iso(job.created_at), "started_at": iso(job.started_at),
            "finished_at": iso(job.finished_at), "source_results": job.source_results}


def enqueue(factory, day):
    try:
        with factory.begin() as session:
            active = session.scalar(select(JobRun).where(JobRun.active_slot == 1))
            if active:
                return job_dict(active)
            job = JobRun(id=str(uuid4()), report_date=day, status="queued", active_slot=1, message="已排队，等待 worker 处理")
            session.add(job)
            session.flush()
            return job_dict(job)
    except IntegrityError:
        # The DB unique slot is the final guard when two requests race.
        with factory() as session:
            active = session.scalar(select(JobRun).where(JobRun.active_slot == 1))
            if active:
                return job_dict(active)
        raise


def ensure_due(factory, settings):
    day = due_today(settings)
    if day:
        with factory() as session:
            exists = session.scalar(select(JobRun.id).where(JobRun.report_date == day).limit(1))
        if not exists:
            enqueue(factory, day)


def recover_interrupted(factory):
    # Called only after acquiring the cross-platform exclusive worker lock.
    with factory.begin() as session:
        session.execute(update(JobRun).where(JobRun.status == "running").values(
            status="failed", active_slot=None, finished_at=utcnow(), message="上次执行因进程停止中断，旧日报已保留；可手动重试"))


def claim_next(factory):
    with factory.begin() as session:
        job = session.scalar(select(JobRun).where(JobRun.status == "queued").order_by(JobRun.created_at).limit(1))
        if not job:
            return None
        result = session.execute(update(JobRun).where(JobRun.id == job.id, JobRun.status == "queued").values(
            status="running", started_at=utcnow(), message="开始采集新闻"))
        return job.id if result.rowcount == 1 else None
