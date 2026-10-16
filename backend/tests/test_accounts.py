from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select, delete
from app.main import create_app
from app.clock import utcnow
from app.models import ReportItem
from app.user_models import AuthSession, User
from conftest import DAY
from test_pipeline import run_report

ORIGIN = {"Origin": "http://localhost:3000"}


def login_client(client, name="reader", platform="android"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": name,
            "password": "Strong-Password-123",
            "display_name": "新闻读者",
            "platform": platform,
        },
        headers=ORIGIN if platform == "web" else {},
    )
    assert response.status_code == 201, response.text
    if platform != "web":
        client.headers["Authorization"] = "Bearer " + response.json()["access_token"]
    return response


def test_cookie_session_origin_and_revocation(env):
    with TestClient(create_app(*env)) as c:
        r = login_client(c, platform="web")
        assert (
            "access_token" not in r.json()
            and "HttpOnly" in r.headers["set-cookie"]
            and "SameSite=strict" in r.headers["set-cookie"]
        )
        assert c.get("/api/v1/auth/me").json()["username"] == "reader"
        assert c.post("/api/v1/tags", json={"name": "金融"}).status_code == 403
        assert (
            c.post(
                "/api/v1/tags",
                json={"name": "金融"},
                headers={"Origin": "https://evil.example"},
            ).status_code
            == 403
        )
        assert c.post("/api/v1/auth/logout", headers=ORIGIN).status_code == 200
        assert c.get("/api/v1/auth/me").status_code == 401


def test_hashed_tokens_password_revokes_all_and_expiry(env):
    with TestClient(create_app(*env)) as c:
        token = login_client(c).json()["access_token"]
        with env[1]() as db:
            assert db.scalar(select(User)).password_hash.startswith("$argon2id$")
            assert db.scalar(select(AuthSession)).token_hash != token
        other = c.post(
            "/api/v1/auth/login",
            json={
                "username": "READER",
                "password": "Strong-Password-123",
                "platform": "android",
            },
        ).json()["access_token"]
        assert (
            c.post(
                "/api/v1/auth/password",
                json={"current_password": "wrong", "new_password": "another-password"},
            ).status_code
            == 400
        )
        assert (
            c.post(
                "/api/v1/auth/password",
                json={
                    "current_password": "Strong-Password-123",
                    "new_password": "another-password",
                },
            ).status_code
            == 200
        )
        assert c.get("/api/v1/auth/me").status_code == 401
        assert (
            c.get(
                "/api/v1/auth/me", headers={"Authorization": "Bearer " + other}
            ).status_code
            == 401
        )
        token = c.post(
            "/api/v1/auth/login",
            json={
                "username": "reader",
                "password": "another-password",
                "platform": "android",
            },
        ).json()["access_token"]
        c.headers["Authorization"] = "Bearer " + token
        with env[1].begin() as db:
            for row in db.scalars(select(AuthSession)):
                row.expires_at = utcnow() - timedelta(seconds=1)
        assert c.get("/api/v1/auth/me").status_code == 401


def test_registration_validation_and_rate_limit(env):
    with TestClient(
        create_app(env[0].model_copy(update={"auth_rate_limit": 3}), env[1])
    ) as c:
        login_client(c)
        data = {
            "username": "reader",
            "password": "Strong-Password-123",
            "display_name": "读者",
            "platform": "android",
        }
        assert c.post("/api/v1/auth/register", json=data).status_code == 409
        data["password"] = "weak"
        assert c.post("/api/v1/auth/register", json=data).status_code == 422
        data["password"] = "wrong-password"
        assert c.post("/api/v1/auth/login", json=data).status_code == 401
        assert c.post("/api/v1/auth/login", json=data).status_code == 429


def test_collections_private_idempotent_snapshot_and_tag_ownership(env):
    run_report(env)
    app = create_app(*env)
    with TestClient(app) as a, TestClient(app) as b:
        login_client(a, "alice")
        login_client(b, "bobby")
        item = a.get(f"/api/v1/reports/{DAY}").json()["items"][0]
        news_id = item["id"]
        path = f"/api/v1/bookmarks/{news_id}"
        tag = a.post("/api/v1/tags", json={"name": "重要"}).json()
        assert a.post("/api/v1/tags", json={"name": " 重要 "}).status_code == 409
        for _ in range(2):
            assert (
                a.put(
                    path, json={"report_date": str(DAY), "tag_ids": [tag["id"]]}
                ).status_code
                == 200
            )
        assert a.get("/api/v1/bookmarks").json()["total"] == 1
        assert b.get(path).status_code == 404
        assert b.put(path, json={"tag_ids": [tag["id"]]}).status_code == 404
        assert b.get("/api/v1/bookmarks").json()["total"] == 0
        assert (
            b.patch(f"/api/v1/tags/{tag['id']}", json={"name": "越权"}).status_code
            == 404
        )
        assert a.get(f"/api/v1/bookmarks?tag_id={tag['id']}").json()["total"] == 1
        with env[1].begin() as db:
            db.execute(delete(ReportItem).where(ReportItem.news_id == news_id))
        assert a.get(path).json()["news"]["title"] == item["title"]
        assert a.get(f"/api/v1/news/{news_id}").status_code == 404
        assert a.delete(f"/api/v1/tags/{tag['id']}").status_code == 200
        assert a.get(path).json()["tags"] == []
        assert a.get("/api/v1/bookmarks/ids").json() == [news_id]
        a.delete(path)
        assert a.get("/api/v1/bookmarks").json()["total"] == 0


def test_chinese_search_filters_pagination_and_escaped_wildcards(env):
    run_report(env)
    with TestClient(create_app(*env)) as c:
        assert c.get("/api/v1/search?q=人工智能").json()["total"] == 2
        assert c.get("/api/v1/search?q=人工智能&region=china").json()["total"] == 1
        assert c.get("/api/v1/search?category=finance&page_size=1").json()["total"] == 2
        assert (
            len(
                c.get("/api/v1/search?category=finance&page_size=1&page=2").json()[
                    "items"
                ]
            )
            == 1
        )
        for q in ["%25", "%27%20OR%201%3D1"]:
            assert c.get("/api/v1/search?q=" + q).json()["total"] == 0
        assert c.get("/api/v1/search?date_from=2027-01-01").json()["total"] == 0
        assert (
            c.get("/api/v1/search?date_from=2027-01-01&date_to=2020-01-01").status_code
            == 422
        )
        assert c.get("/api/v1/bookmarks").status_code == 401
