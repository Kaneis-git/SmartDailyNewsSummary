# Web 与 App 共用的 API 入口；采集、生成和通知发送由独立 worker 执行。
from contextlib import asynccontextmanager
from datetime import date, datetime
import secrets
from fastapi import FastAPI, HTTPException, Query, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import Response
from sqlalchemy import select
from .clock import due_today, local_now, utcnow
from .config import get_settings
from .db import make_session_factory, sync_sources
from .jobs import enqueue, job_dict
from .models import DailyReport, JobRun, ReportItem, RuntimeState, Source
from .reports import as_markdown, report_dict
from .auth import router as auth_router, current_identity, Identity
from .collections import router as collection_router
from .notifications import router as notification_router


def create_app(settings=None, factory=None):
    settings = settings or get_settings()
    factory = factory or make_session_factory(settings.db_url)

    @asynccontextmanager
    async def lifespan(app):
        sync_sources(factory, settings.sources_file)
        yield

    app = FastAPI(title="AI Daily News Assistant", version="0.4.0", lifespan=lifespan)
    app.state.factory, app.state.settings = factory, settings
    origins = [v.strip() for v in settings.allowed_origins.split(",") if v.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-Admin-Token", "Authorization"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=[v.strip() for v in settings.allowed_hosts.split(",")])
    prefix = "/api/v1"
    for router in (auth_router, collection_router, notification_router): app.include_router(router,prefix=prefix)

    @app.get(prefix + "/health")
    def health():
        with factory() as session:
            state = session.get(RuntimeState, "worker_heartbeat")
        alive = False
        if state:
            try:
                age = (utcnow() - datetime.fromisoformat(state.value)).total_seconds()
                alive = 0 <= age < 45
            except ValueError:
                pass
        return {"status": "ok", "worker_online": alive, "ai_enabled": settings.ai_enabled,
                "ai_model": settings.ai_model if settings.ai_enabled else None,
                "timezone": settings.timezone, "schedule": f"{settings.report_hour:02}:{settings.report_minute:02}",
                "today": local_now(settings).date().isoformat(), "report_due": due_today(settings) is not None,
                "token_required": bool(settings.admin_token), "registration_enabled": settings.allow_registration,"max_per_section": settings.max_per_section, "push_enabled": settings.push_enabled,"version":"0.4.0"}

    @app.get(prefix + "/reports")
    def list_reports(limit: int = Query(30, ge=1, le=366), before: date | None = None):
        query = select(DailyReport).order_by(DailyReport.report_date.desc()).limit(limit)
        if before:
            query = query.where(DailyReport.report_date < before)
        with factory() as session:
            return [report_dict(session, report, False) for report in session.scalars(query)]

    def load_report(day):
        with factory() as session:
            report = session.scalar(select(DailyReport).where(DailyReport.report_date == day))
            if not report:
                raise HTTPException(404, "该日期尚未生成日报")
            return report_dict(session, report)

    @app.get(prefix + "/reports/{day}")
    def get_report(day: date):
        return load_report(day)

    @app.get(prefix + "/reports/{day}/markdown")
    def download_report(day: date):
        return Response(as_markdown(load_report(day)), media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="daily-news-{day.isoformat()}.md"'})

    @app.get(prefix + "/news/{news_id}")
    def news_detail(news_id: int, report_date: date | None = None):
        query = select(ReportItem).join(DailyReport).where(ReportItem.news_id == news_id)
        if report_date:
            query = query.where(DailyReport.report_date == report_date)
        query = query.order_by(DailyReport.report_date.desc()).limit(1)
        with factory() as session:
            item = session.scalar(query)
            if not item:
                raise HTTPException(404, "该新闻未收录在指定日报中")
            related = list(session.scalars(select(ReportItem).where(ReportItem.report_id == item.report_id,
                ReportItem.news_id != news_id, ReportItem.region == item.region, ReportItem.category == item.category).limit(3)))
            return {**item.snapshot, "related": [r.snapshot for r in related]}

    @app.get(prefix + "/sources")
    def list_sources():
        with factory() as session:
            recent = session.scalar(select(JobRun).order_by(JobRun.created_at.desc()).limit(1))
            results = {r["id"]: r for r in recent.source_results} if recent else {}
            return [{"id": s.id, "name": s.name, "feed_url": s.feed_url, "region_hint": s.region_hint,
                     "category_hint": s.category_hint, "enabled": s.enabled, "last_result": results.get(s.id)}
                    for s in session.scalars(select(Source).order_by(Source.id))]

    @app.post(prefix + "/runs", status_code=202)
    def request_run(request: Request, identity: Identity = Depends(current_identity)):
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            raise HTTPException(403, "不允许此网页来源触发任务")
        token = request.headers.get("x-admin-token", "")
        if settings.admin_token and not secrets.compare_digest(token, settings.admin_token):
            raise HTTPException(403, "请输入正确的管理口令")
        day = due_today(settings)
        if day is None:
            raise HTTPException(409, "今日早报尚未到截止时间，请先查看历史日报")
        return enqueue(factory, day)

    @app.get(prefix + "/runs/latest")
    def latest_run():
        with factory() as session:
            row = session.scalar(select(JobRun).order_by(JobRun.created_at.desc()).limit(1))
            return job_dict(row) if row else None

    @app.get(prefix + "/runs/{job_id}")
    def get_run(job_id: str):
        with factory() as session:
            row = session.get(JobRun, job_id)
            if not row:
                raise HTTPException(404, "任务不存在")
            return job_dict(row)

    return app


app = create_app()
