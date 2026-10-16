"""Four-category publishing, API compatibility and classification regressions."""
from datetime import timedelta
from email.utils import format_datetime
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import delete, select
from ai_service.classifier import classify
from app.config import Settings
from app.main import create_app
from app.models import DailyReport, ReportItem
from app.models import NewsAnalysis
from app.pipeline import analysis_for, persist_news
from app.feeds import parse_feed
from app.clock import window
from ai_service.analyzer import extractive
from app.reports import report_dict
from conftest import DAY, PUBLISHED, entry, rss, eight_feeds
from test_pipeline import run_report
from test_accounts import login_client


@pytest.mark.parametrize("title,region,category", [
    ("AI芯片技术进展", "international", "ai"),
    ("Artificial intelligence policy and finance", "international", "ai"),
    ("中国发布大模型安全政策", "china", "ai"),
    ("DeepSeek releases a new model", "china", "ai"),
    ("OpenAI raises investment for ChatGPT", "international", "ai"),
    ("Qwen模型更新", "china", "ai"),
    ("GPU chip software update", "international", "technology"),
    ("Airline shares rise on economic outlook", "international", "finance"),
    ("Fair trade policy announced", "international", "finance"),
    ("Railway minister said talks will resume", "international", "politics"),
])
def test_ai_is_separate_and_does_not_match_unrelated_words(title, region, category):
    item = dict(title=title, text_excerpt="", region_hint="international", category_hint="mixed")
    assert classify(item)[:2] == (region, category)


def test_settings_default_ten_and_validate_range():
    assert Settings(_env_file=None).max_per_section == 10
    for limit in (0, 11):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, max_per_section=limit)


def test_ambiguous_agent_and_model_names_require_context():
    item = dict(title='Agent企业智能化落地报告', text_excerpt='', region_hint='china', category_hint='ai')
    assert classify(item)[1] == 'ai'
    assert classify({**item, 'title': 'Claude model update', 'category_hint': 'technology'})[1] == 'ai'
    assert classify({**item, 'title': 'Government foreign agent policy', 'category_hint': 'politics'})[1] == 'politics'
    assert classify({**item, 'title': 'Gemini space technology', 'category_hint': 'technology'})[1] == 'technology'


def many_feeds(source, settings):
    titles = {"politics": "政府政策调整", "finance": "央行货币利率调整",
              "technology": "半导体芯片研发", "ai": "人工智能大模型应用发布"}
    return rss([entry(title=f"{titles[source.category_hint]} {source.id} {i}",
        url=f"https://news.example/{source.id}/{i}",
        published=format_datetime(PUBLISHED + timedelta(minutes=i))) for i in range(15)])


def test_eight_sections_publish_ten_each_and_sort_and_deduplicate(env):
    run_report(env, many_feeds)
    run_report(env, many_feeds)
    with env[1]() as db:
        report = report_dict(db, db.scalar(select(DailyReport)))
    assert report["total"] == len(report["items"]) == 80
    assert len(report["coverage"]) == 8
    assert set(report["coverage"].values()) == {10}
    assert len({item["id"] for item in report["items"]}) == 80
    for section in report["coverage"]:
        region, category = section.split(".")
        rows = [item for item in report["items"] if item["analysis"]["region"] == region
                and item["analysis"]["category"] == category]
        assert [int(item["url"].rsplit("/", 1)[1]) for item in rows] == list(range(14, 4, -1))


def test_higher_importance_precedes_newer_ai_articles(env):
    def feed(source, settings):
        if source.category_hint != 'ai':
            return rss([])
        return rss([entry(title=f"AI model {source.id} {i}" + (' breakthrough' if i == 0 else ''),
            url=f'https://news.example/{source.id}/{i}',
            published=format_datetime(PUBLISHED + timedelta(minutes=i))) for i in range(15)])
    run_report(env, feed)
    with env[1]() as db:
        report = report_dict(db, db.scalar(select(DailyReport)))
    for region in ('china', 'international'):
        rows = [i for i in report['items'] if i['analysis']['region'] == region]
        assert len(rows) == 10 and rows[0]['url'].endswith('/0')
        assert rows[0]['analysis']['importance'] > rows[1]['analysis']['importance']


def test_ai_search_detail_export_and_bookmark_snapshot(env):
    run_report(env, many_feeds)
    with TestClient(create_app(*env)) as c:
        assert c.get('/api/v1/health').json()['max_per_section'] == 10
        rows = c.get('/api/v1/search?category=ai&region=china').json()
        assert rows['total'] == len(rows['items']) == 10
        item = rows['items'][0]
        assert c.get(f"/api/v1/news/{item['id']}").json()['analysis']['category'] == 'ai'
        assert c.get('/api/v1/search?category=invalid').status_code == 422
        exported = c.get(f'/api/v1/reports/{DAY}/markdown').text
        assert exported.count('### AI 人工智能') == 2
        assert exported.count('#### ') == 80
        login_client(c)
        saved = c.put(f"/api/v1/bookmarks/{item['id']}", json={'report_date': str(DAY)}).json()
        run_report(env, eight_feeds)
        assert c.get(f"/api/v1/bookmarks/{item['id']}").json()['news'] == saved['news']


def test_legacy_six_section_report_stays_readable_without_rewrite(env):
    run_report(env)
    with env[1].begin() as db:
        report = db.scalar(select(DailyReport))
        db.execute(delete(ReportItem).where(ReportItem.category == 'ai'))
        report.coverage = {k: v for k, v in report.coverage.items() if not k.endswith('.ai')}
    with env[1]() as db:
        before = report_dict(db, db.scalar(select(DailyReport)))
    with TestClient(create_app(*env)) as c:
        result = c.get(f'/api/v1/reports/{DAY}').json()
        assert result == before and result['total'] == 6
        assert c.get(f'/api/v1/reports/{DAY}/markdown').status_code == 200


def test_old_model_cache_does_not_keep_ai_in_technology(env, source, monkeypatch):
    from app.feeds import digest
    settings = env[0].model_copy(update={'ai_base_url': 'https://model.example/v1', 'ai_model': 'test'})
    item = parse_feed(rss([entry(title='人工智能芯片研发')]), source, *window(DAY, settings))[0][0]
    news_id = persist_news(env[1], item)
    old = extractive(item).model_dump()
    old['category'] = 'technology'
    with env[1].begin() as db:
        db.add(NewsAnalysis(news_id=news_id, content_hash=item['content_hash'],
            model='test@' + digest(settings.ai_base_url)[:12], prompt_version='news-v1.0', status='ai', payload=old))
    calls = []
    def fresh(item, settings):
        calls.append(1)
        return extractive(item).model_dump(), 'ai'
    monkeypatch.setattr('app.pipeline.analyze', fresh)
    assert analysis_for(env[1], item, news_id, settings)[1]['category'] == 'ai'
    assert analysis_for(env[1], item, news_id, settings)[1]['category'] == 'ai'
    assert len(calls) == 1
    with env[1]() as db:
        assert db.scalar(select(NewsAnalysis).where(NewsAnalysis.prompt_version == 'news-v1.0')).payload == old
