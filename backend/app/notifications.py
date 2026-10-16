"""Transactional outbox; provider acceptance does not prove device delivery."""

from datetime import timedelta
from uuid import UUID, uuid4
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, update, func
from sqlalchemy.dialects.sqlite import insert
from .auth import Identity, current_identity, digest
from .clock import utcnow
from .user_models import AuthSession, Device, NotificationDelivery

router = APIRouter(tags=["mobile notifications"])


class DeviceInput(BaseModel):
    installation_id: UUID
    registration_id: str = Field(
        min_length=8, max_length=128, pattern=r"^[A-Za-z0-9_-]+$"
    )


@router.get("/mobile/config")
def mobile_config(request: Request):
    s = request.app.state.settings
    return {
        "push_enabled": s.push_enabled,
        "provider": s.push_provider,
        "app_key": s.jpush_app_key if s.push_enabled else None,
        "timezone": s.timezone,
        "schedule": f"{s.report_hour:02}:{s.report_minute:02}",
    }


@router.post("/devices")
def register_device(
    payload: DeviceInput,
    request: Request,
    identity: Identity = Depends(current_identity),
):
    if not request.app.state.settings.push_enabled:
        raise HTTPException(409, "服务器尚未配置消息推送")
    with request.app.state.factory.begin() as db:
        db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        auth = db.get(AuthSession, identity.session_id)
        if auth.revoked or auth.expires_at <= utcnow():
            raise HTTPException(401, "登录已失效")
        if auth.platform != "android":
            raise HTTPException(422, "当前仅支持 Android 通知订阅")
        hashed = digest(payload.registration_id)
        row = db.scalar(
            select(Device).where(
                Device.user_id == identity.user_id,
                Device.installation_id == str(payload.installation_id),
            )
        )
        if (
            row
            and row.enabled
            and row.session_id == identity.session_id
            and row.token_hash == hashed
        ):
            return {"id": row.id, "enabled": True}
        old_ids = list(db.scalars(select(Device.id).where(Device.token_hash == hashed)))
        if old_ids:
            db.execute(
                update(Device).where(Device.id.in_(old_ids)).values(enabled=False)
            )
            db.execute(
                update(NotificationDelivery)
                .where(
                    NotificationDelivery.device_id.in_(old_ids),
                    NotificationDelivery.status == "pending",
                )
                .values(
                    status="cancelled", finished_at=utcnow(), message="设备订阅已更新"
                )
            )
        if not row:
            if (
                db.scalar(
                    select(func.count())
                    .select_from(Device)
                    .where(Device.user_id == identity.user_id)
                )
                >= 20
            ):
                raise HTTPException(
                    409, "设备记录已达 20 条上限，请联系服务管理员清理旧记录"
                )
            row = Device(
                id=str(uuid4()),
                user_id=identity.user_id,
                installation_id=str(payload.installation_id),
            )
            db.add(row)
        row.session_id, row.provider, row.registration_id = (
            identity.session_id,
            "jpush",
            payload.registration_id,
        )
        row.token_hash, row.enabled, row.updated_at = hashed, True, utcnow()
        db.flush()
        return {"id": row.id, "enabled": True}


@router.get("/devices")
def list_devices(request: Request, identity: Identity = Depends(current_identity)):
    with request.app.state.factory() as db:
        return [
            {
                "id": d.id,
                "enabled": d.enabled,
                "updated_at": d.updated_at.isoformat() + "Z",
                "current_session": d.session_id == identity.session_id,
            }
            for d in db.scalars(
                select(Device).where(Device.user_id == identity.user_id)
            )
        ]


@router.delete("/devices/{device_id}")
def disable_device(
    device_id: str, request: Request, identity: Identity = Depends(current_identity)
):
    with request.app.state.factory.begin() as db:
        row = db.get(Device, device_id)
        if row and row.user_id == identity.user_id:
            db.execute(
                update(NotificationDelivery)
                .where(
                    NotificationDelivery.device_id == device_id,
                    NotificationDelivery.status == "pending",
                )
                .values(status="cancelled", finished_at=utcnow(), message="订阅已取消")
            )
            row.enabled = False
    return {"ok": True}


@router.get("/notifications/deliveries")
def list_deliveries(request: Request, identity: Identity = Depends(current_identity)):
    with request.app.state.factory() as db:
        return [
            {
                "id": d.id,
                "report_date": d.report_date.isoformat(),
                "status": d.status,
                "message": d.message,
                "attempts": d.attempts,
            }
            for d in db.scalars(
                select(NotificationDelivery)
                .where(NotificationDelivery.user_id == identity.user_id)
                .order_by(NotificationDelivery.created_at.desc())
                .limit(50)
            )
        ]


def queue_report_notifications(db, report, settings):
    if not settings.push_enabled or report.status == "empty":
        return
    for d in db.scalars(
        select(Device)
        .join(AuthSession)
        .where(
            Device.enabled.is_(True),
            AuthSession.revoked.is_(False),
            AuthSession.expires_at > utcnow(),
        )
    ):
        db.execute(
            insert(NotificationDelivery)
            .values(
                id=str(uuid4()),
                device_id=d.id,
                user_id=d.user_id,
                report_id=report.id,
                report_date=report.report_date,
                status="pending",
                attempts=0,
                next_attempt_at=utcnow(),
                created_at=utcnow(),
                message="等待推送",
            )
            .on_conflict_do_nothing(index_elements=["device_id", "report_date"])
        )


def recover_notifications(factory):
    with factory.begin() as db:
        db.execute(
            update(NotificationDelivery)
            .where(NotificationDelivery.status == "sending")
            .values(
                status="unknown",
                message="发送期间进程中断，受理状态未知；不自动重发",
                finished_at=utcnow(),
            )
        )


def send_jpush(settings, token, day, delivery_id, client):
    payload = {
        "platform": "android",
        "audience": {"registration_id": [token]},
        "notification": {
            "android": {
                "alert": "今日新闻已生成，点击查看",
                "title": f"{day} 全球新闻日报",
                "extras": {"report_date": str(day), "delivery_id": delivery_id},
            }
        },
        "options": {"time_to_live": 86400},
    }
    response = client.post(
        "https://api.jpush.cn/v3/push",
        json=payload,
        auth=(settings.jpush_app_key, settings.jpush_master_secret),
    )
    if response.status_code == 429:
        return "retry", "推送服务限流，稍后重试", None
    if response.status_code >= 500:
        return "unknown", "推送服务响应异常，是否受理未知；不自动重发", None
    if response.status_code != 200:
        return (
            "failed",
            f"推送服务拒绝请求（HTTP {response.status_code}），请检查配置与设备",
            None,
        )
    try:
        receipt = str(response.json()["msg_id"])
        if not receipt or len(receipt) > 200:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        return "unknown", "推送回执格式异常；不自动重发", None
    return "accepted", "推送服务已受理，设备是否展示需在真机确认", receipt


def dispatch_notifications(factory, settings, client=None):
    if not settings.push_enabled:
        return
    owned = client is None
    client = client or httpx.Client(
        timeout=settings.push_timeout, follow_redirects=False
    )
    try:
        for _ in range(20):
            with factory.begin() as db:
                db.connection().exec_driver_sql("BEGIN IMMEDIATE")
                row = db.scalar(
                    select(NotificationDelivery)
                    .where(
                        NotificationDelivery.status == "pending",
                        NotificationDelivery.next_attempt_at <= utcnow(),
                    )
                    .order_by(NotificationDelivery.created_at)
                    .limit(1)
                )
                if not row:
                    break
                device = db.get(Device, row.device_id)
                auth = db.get(AuthSession, device.session_id) if device else None
                if (
                    not device
                    or not device.enabled
                    or not auth
                    or auth.revoked
                    or auth.expires_at <= utcnow()
                ):
                    row.status, row.message, row.finished_at = (
                        "cancelled",
                        "订阅或登录已失效",
                        utcnow(),
                    )
                    continue
                if row.created_at < utcnow() - timedelta(days=1):
                    row.status, row.message, row.finished_at = (
                        "cancelled",
                        "通知已超过 24 小时有效期",
                        utcnow(),
                    )
                    continue
                row.status, row.attempts = "sending", row.attempts + 1
                identifier, day, token = row.id, row.report_date, device.registration_id
            try:
                status, message, receipt = send_jpush(
                    settings, token, day, identifier, client
                )
            except (httpx.ConnectTimeout, httpx.ConnectError, httpx.PoolTimeout):
                status, message, receipt = "retry", "尚未建立连接，稍后重试", None
            except httpx.HTTPError:
                status, message, receipt = (
                    "unknown",
                    "发送结果未知；为避免重复提醒，不自动重发",
                    None,
                )
            with factory.begin() as db:
                row = db.get(NotificationDelivery, identifier)
                if status == "retry":
                    if row.attempts >= 4:
                        status, message = "failed", "已达 4 次尝试上限"
                    else:
                        status = "pending"
                        row.next_attempt_at = utcnow() + timedelta(
                            seconds=60 * 2 ** (row.attempts - 1)
                        )
                row.status, row.message, row.receipt = status, message, receipt
                row.finished_at = utcnow() if status != "pending" else None
    finally:
        if owned:
            client.close()
