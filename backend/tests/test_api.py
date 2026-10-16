from fastapi.testclient import TestClient
from app.main import create_app
from conftest import DAY
from test_pipeline import run_report
from test_accounts import login_client


def test_report_history_detail_and_download(env):
    run_report(env)
    with TestClient(create_app(*env)) as client:
        report=client.get(f"/api/v1/reports/{DAY}").json()
        assert report["total"]==8
        assert client.get('/api/v1/reports').json()[0]["date"]==str(DAY)
        assert client.get('/api/v1/reports?before=2026-10-12').json()==[]
        detail=client.get(f"/api/v1/news/{report['items'][0]['id']}?report_date={DAY}").json()
        assert detail["url"].startswith("https://news.example/")
        markdown=client.get(f"/api/v1/reports/{DAY}/markdown")
        assert markdown.status_code==200 and "中国新闻" in markdown.text and "extractive" in markdown.text
        assert "attachment" in markdown.headers["content-disposition"]
        assert client.get('/api/v1/reports/2020-01-01').status_code==404
        assert client.get('/api/v1/reports/not-a-date').status_code==422
        assert client.get('/api/v1/reports?limit=1000').status_code==422


def test_run_api_idempotence_and_latest_route(env,monkeypatch):
    monkeypatch.setattr("app.main.due_today",lambda settings:DAY)
    with TestClient(create_app(*env)) as client:
        login_client(client)
        assert client.get('/api/v1/runs/latest').json() is None
        first=client.post('/api/v1/runs');second=client.post('/api/v1/runs')
        assert first.status_code==202 and first.json()["id"]==second.json()["id"]
        assert client.get('/api/v1/runs/latest').json()["id"]==first.json()["id"]


def test_no_generation_before_cutoff(env,monkeypatch):
    monkeypatch.setattr("app.main.due_today",lambda settings:None)
    with TestClient(create_app(*env)) as client:
        login_client(client)
        assert client.post('/api/v1/runs').status_code==409


def test_trigger_origin_and_operator_token(env,monkeypatch):
    monkeypatch.setattr("app.main.due_today",lambda settings:DAY)
    settings=env[0].model_copy(update={"admin_token":"fixture-token"})
    with TestClient(create_app(settings,env[1])) as client:
        login_client(client)
        assert client.post('/api/v1/runs',headers={"origin":"https://unknown.example"}).status_code==403
        assert client.post('/api/v1/runs').status_code==403
        assert client.post('/api/v1/runs',headers={"x-admin-token":"fixture-token"}).status_code==202
        assert "fixture-token" not in client.get('/api/v1/health').text
        assert client.get('/api/v1/health',headers={"host":"unknown.example"}).status_code==400
