from datetime import timedelta
from uuid import uuid4
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import create_app
from app.clock import utcnow
from app.notifications import dispatch_notifications, recover_notifications
from app.user_models import Device, NotificationDelivery
from test_accounts import login_client
from test_pipeline import run_report
from conftest import rss


def setup_push(env):
    return env[0].model_copy(
        update={
            "push_provider": "jpush",
            "jpush_app_key": "test-public-key",
            "jpush_master_secret": "test-secret",
        }
    ), env[1]


def device(c, installation=None, token="test-registration-token"):
    r = c.post(
        "/api/v1/devices",
        json={
            "installation_id": installation or str(uuid4()),
            "registration_id": token,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_outbox_dedup_subscription_refresh_acceptance_and_logout(env):
    env = setup_push(env)
    with TestClient(create_app(*env)) as c:
        login_client(c)
        installation = str(uuid4())
        identifier = device(c, installation)
        assert "test-secret" not in c.get("/api/v1/mobile/config").text
        run_report(env)
        run_report(env)
        device(c, installation)
        with env[1]() as db:
            assert (
                db.scalar(select(func.count()).select_from(NotificationDelivery)) == 1
            )
        calls = []

        def handler(r):
            calls.append(r)
            return httpx.Response(200, json={"msg_id": "123"})

        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            dispatch_notifications(env[1], env[0], transport)
            dispatch_notifications(env[1], env[0], transport)
        assert len(calls) == 1 and b"report_date" in calls[0].content
        assert (
            c.get("/api/v1/notifications/deliveries").json()[0]["status"] == "accepted"
        )
        c.post("/api/v1/auth/logout")
        with env[1]() as db:
            assert not db.get(Device, identifier).enabled


def test_empty_failed_reports_and_disabled_push(env):
    with TestClient(create_app(*env)) as c:
        login_client(c)
        assert (
            c.post(
                "/api/v1/devices",
                json={
                    "installation_id": str(uuid4()),
                    "registration_id": "valid-registration",
                },
            ).status_code
            == 409
        )
    env = setup_push(env)
    with TestClient(create_app(*env)) as c:
        login_client(c, "pushuser")
        device(c)
        run_report(env, lambda *_: rss([]))

        def broken(*_):
            raise ValueError("fixture")

        run_report(env, broken)
        assert c.get("/api/v1/notifications/deliveries").json() == []


def test_timeout_is_unknown_and_not_resent(env):
    env = setup_push(env)
    with TestClient(create_app(*env)) as c:
        login_client(c)
        device(c)
        run_report(env)
        calls = []

        def handler(r):
            calls.append(r)
            raise httpx.ReadTimeout("fixture", request=r)

        with httpx.Client(transport=httpx.MockTransport(handler)) as transport:
            dispatch_notifications(env[1], env[0], transport)
            dispatch_notifications(env[1], env[0], transport)
        assert (
            len(calls) == 1
            and c.get("/api/v1/notifications/deliveries").json()[0]["status"]
            == "unknown"
        )


def test_retry_cancel_private_devices_and_crash_recovery(env):
    env = setup_push(env)
    app = create_app(*env)
    with TestClient(app) as a, TestClient(app) as b:
        login_client(a, "alice")
        login_client(b, "bobby")
        identifier = device(a)
        run_report(env)
        b.delete("/api/v1/devices/" + identifier)
        assert (
            b.get("/api/v1/devices").json() == []
            and b.get("/api/v1/notifications/deliveries").json() == []
        )
        with httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(429))
        ) as transport:
            dispatch_notifications(env[1], env[0], transport)
        with env[1].begin() as db:
            row = db.scalar(select(NotificationDelivery))
            assert (
                row.status == "pending"
                and row.attempts == 1
                and row.next_attempt_at > utcnow()
            )
            row.status = "sending"
        recover_notifications(env[1])
        assert (
            a.get("/api/v1/notifications/deliveries").json()[0]["status"] == "unknown"
        )
        with env[1].begin() as db:
            row = db.scalar(select(NotificationDelivery))
            row.status = "pending"
            row.next_attempt_at = utcnow() - timedelta(seconds=1)
        a.delete("/api/v1/devices/" + identifier)
        assert (
            a.get("/api/v1/notifications/deliveries").json()[0]["status"] == "cancelled"
        )


def test_account_switch_disables_old_push_binding(env):
    env = setup_push(env)
    app = create_app(*env)
    with TestClient(app) as a, TestClient(app) as b:
        login_client(a, "alice")
        login_client(b, "bobby")
        identifier = device(a)
        run_report(env)
        device(b)
        with env[1]() as db:
            assert (
                not db.get(Device, identifier).enabled
                and db.scalar(select(NotificationDelivery)).status == "cancelled"
            )
