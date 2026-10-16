"""Revocable opaque sessions: HttpOnly cookies for Web, bearer tokens for App."""

from dataclasses import dataclass
from datetime import timedelta
import hashlib, re, secrets, time
from typing import Literal
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import case, select, update, delete
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.exc import IntegrityError
from .clock import utcnow
from .user_models import AuthRate, AuthSession, Device, NotificationDelivery, User

router = APIRouter(prefix="/auth", tags=["accounts"])
COOKIE = "daily_news_session"
hasher = PasswordHasher(time_cost=3, memory_cost=19456, parallelism=1)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=10, max_length=128)
    platform: Literal["web", "android", "ios"] = "web"

    @field_validator("username")
    @classmethod
    def valid_username(cls, value):
        if not re.fullmatch(r"[A-Za-z0-9_]{3,32}", value):
            raise ValueError("用户名须为 3–32 位英文字母、数字或下划线")
        return value.casefold()


class Registration(Credentials):
    display_name: str = Field(min_length=1, max_length=60)

    @field_validator("display_name")
    @classmethod
    def valid_name(cls, value):
        if not value.strip():
            raise ValueError("昵称不可为空")
        return value.strip()


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


@dataclass(frozen=True)
class Identity:
    user_id: int
    session_id: str


def user_dict(user):
    return {"id": user.id, "username": user.username, "display_name": user.display_name}


def check_origin(request):
    origin = request.headers.get("origin")
    if origin and origin not in [
        v.strip() for v in request.app.state.settings.allowed_origins.split(",")
    ]:
        raise HTTPException(403, "不允许此网页来源")
    if (
        request.cookies.get(COOKIE)
        and not origin
        and not request.headers.get("authorization")
    ):
        raise HTTPException(403, "浏览器操作需要 Origin 请求头")


def current_identity(request: Request):
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        check_origin(request)
    auth = request.headers.get("authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else request.cookies.get(COOKIE, "")
    if not token or len(token) > 256:
        raise HTTPException(401, "请先登录")
    with request.app.state.factory() as db:
        row = db.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == digest(token),
                AuthSession.revoked.is_(False),
                AuthSession.expires_at > utcnow(),
            )
        )
        if not row:
            raise HTTPException(401, "登录已失效，请重新登录")
        return Identity(row.user_id, row.id)


def rate_limit(request, username):
    window = int(time.time()) // 900
    ip = request.client.host if request.client else "unknown"
    denied = False
    with request.app.state.factory.begin() as db:
        db.execute(delete(AuthRate).where(AuthRate.window < window - 2))
        for key, limit in (
            ("ip:" + ip, 60),
            ("user:" + username, request.app.state.settings.auth_rate_limit),
        ):
            key = digest(key)
            stmt = insert(AuthRate).values(key=key, window=window, count=1)
            db.execute(
                stmt.on_conflict_do_update(
                    index_elements=[AuthRate.key],
                    set_={
                        "window": window,
                        "count": case(
                            (AuthRate.window == window, AuthRate.count + 1), else_=1
                        ),
                    },
                )
            )
            denied |= db.get(AuthRate, key).count > limit
    if denied:
        raise HTTPException(
            429, "尝试过于频繁，请 15 分钟后重试", headers={"Retry-After": "900"}
        )


def verify_password(encoded, password):
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError):
        return False


def revoke(db, user_id, session_id=None):
    condition = [AuthSession.user_id == user_id]
    devices = [Device.user_id == user_id]
    if session_id:
        condition.append(AuthSession.id == session_id)
        devices.append(Device.session_id == session_id)
    db.execute(update(AuthSession).where(*condition).values(revoked=True))
    db.execute(
        update(NotificationDelivery)
        .where(
            NotificationDelivery.device_id.in_(select(Device.id).where(*devices)),
            NotificationDelivery.status == "pending",
        )
        .values(status="cancelled", message="订阅已取消", finished_at=utcnow())
    )
    db.execute(update(Device).where(*devices).values(enabled=False))


def new_session(db, request, response, user, platform):
    token = secrets.token_urlsafe(48)
    expires = utcnow() + timedelta(days=request.app.state.settings.session_days)
    active = list(
        db.scalars(
            select(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked.is_(False))
            .order_by(AuthSession.created_at.desc())
        )
    )
    for old in active[9:]:
        revoke(db, user.id, old.id)
    db.add(
        AuthSession(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=digest(token),
            platform=platform,
            expires_at=expires,
        )
    )
    result = {"user": user_dict(user), "expires_at": expires.isoformat() + "Z"}
    if platform == "web":
        response.set_cookie(
            COOKIE,
            token,
            max_age=request.app.state.settings.session_days * 86400,
            httponly=True,
            secure=request.app.state.settings.cookie_secure,
            samesite="strict",
            path="/api/v1",
        )
    else:
        result["access_token"] = token
    return result


def check_login_request(request, payload):
    check_origin(request)
    if payload.platform == "web" and not request.headers.get("origin"):
        raise HTTPException(403, "浏览器登录需要 Origin 请求头")
    rate_limit(request, payload.username)


@router.post("/register", status_code=201)
def register(payload: Registration, request: Request, response: Response):
    check_login_request(request, payload)
    if not request.app.state.settings.allow_registration:
        raise HTTPException(403, "本站已关闭新用户注册")
    encoded = hasher.hash(payload.password)
    try:
        with request.app.state.factory.begin() as db:
            user = User(
                username=payload.username,
                display_name=payload.display_name,
                password_hash=encoded,
            )
            db.add(user)
            db.flush()
            return new_session(db, request, response, user, payload.platform)
    except IntegrityError:
        raise HTTPException(409, "该用户名已被使用")


@router.post("/login")
def login(payload: Credentials, request: Request, response: Response):
    check_login_request(request, payload)
    with request.app.state.factory.begin() as db:
        user = db.scalar(select(User).where(User.username == payload.username))
        valid = verify_password(
            user.password_hash if user else DUMMY_HASH, payload.password
        )
        if not user or not valid:
            raise HTTPException(401, "用户名或密码错误")
        if hasher.check_needs_rehash(user.password_hash):
            user.password_hash = hasher.hash(payload.password)
        return new_session(db, request, response, user, payload.platform)


@router.get("/me")
def me(request: Request, identity: Identity = Depends(current_identity)):
    with request.app.state.factory() as db:
        return user_dict(db.get(User, identity.user_id))


@router.post("/logout")
def logout(
    request: Request, response: Response, identity: Identity = Depends(current_identity)
):
    with request.app.state.factory.begin() as db:
        revoke(db, identity.user_id, identity.session_id)
    response.delete_cookie(COOKIE, path="/api/v1")
    return {"ok": True}


@router.post("/logout-all")
def logout_all(
    request: Request, response: Response, identity: Identity = Depends(current_identity)
):
    with request.app.state.factory.begin() as db:
        revoke(db, identity.user_id)
    response.delete_cookie(COOKIE, path="/api/v1")
    return {"ok": True}


@router.post("/password")
def change_password(
    payload: PasswordChange,
    request: Request,
    response: Response,
    identity: Identity = Depends(current_identity),
):
    rate_limit(request, str(identity.user_id))
    with request.app.state.factory.begin() as db:
        user = db.get(User, identity.user_id)
        if not verify_password(user.password_hash, payload.current_password):
            raise HTTPException(400, "当前密码不正确")
        user.password_hash = hasher.hash(payload.new_password)
        revoke(db, identity.user_id)
    response.delete_cookie(COOKIE, path="/api/v1")
    return {"ok": True, "message": "密码已更新，请在各设备重新登录"}
