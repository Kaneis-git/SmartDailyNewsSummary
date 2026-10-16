import json
import httpx
from ai_service.analyzer import analyze, extractive

ITEM={"title":"AI chip technology fixture", "text_excerpt":"This is a deliberately constructed test excerpt about AI chip technology, not an actual news article.",
      "region_hint":"international", "category_hint":"technology", "source_name":"Test fixture"}


def test_no_key_mode_is_explicit(env):
    result,status=analyze(ITEM,env[0])
    assert status=="extractive" and result["market_impact"]==""
    assert result["category"] == "ai" and result["tags"] == ["AI 人工智能"]
    assert "未配置模型" in result["limitations"][0]


def test_valid_ai_output(env):
    settings=env[0].model_copy(update={"ai_base_url":"https://model.example/v1","ai_model":"test-model"})
    expected=extractive(ITEM).model_dump();expected["summary"]="明确标注的模型测试摘要。";expected["headline"]="模型测试标题"
    def handler(request):
        sent=json.loads(request.content)
        assert sent["messages"][1]["role"]=="user"
        assert "ai 为独立人工智能领域" in sent["messages"][0]["content"]
        assert request.url.path=="/v1/chat/completions"
        return httpx.Response(200,json={"choices":[{"message":{"content":json.dumps(expected)}}]})
    result,status=analyze(ITEM,settings,httpx.MockTransport(handler))
    assert status=="ai" and result["summary"]==expected["summary"]
    assert result["category"] == "ai"


def test_invalid_output_falls_back_without_prediction(env,monkeypatch):
    monkeypatch.setattr("ai_service.analyzer.time.sleep",lambda _:None)
    settings=env[0].model_copy(update={"ai_base_url":"https://model.example/v1","ai_model":"test"})
    calls=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(200,json={"choices":[{"message":{"content":'{"summary":"unsupported"}'}}]})
    result,status=analyze(ITEM,settings,httpx.MockTransport(handler))
    assert len(calls)==2 and status=="fallback" and result["short_term"]==""


def test_auth_failure_not_retried_or_leaked(env):
    settings=env[0].model_copy(update={"ai_base_url":"https://model.example/v1","ai_model":"test","ai_api_key":"test-secret"})
    calls=[]
    def handler(request):
        calls.append(1)
        return httpx.Response(401,text="test-secret must never appear in UI")
    result,status=analyze(ITEM,settings,httpx.MockTransport(handler))
    assert len(calls)==1 and status=="fallback" and "test-secret" not in json.dumps(result)


def test_localhost_lookalike_rejected(env):
    settings=env[0].model_copy(update={"ai_base_url":"http://localhost.evil.example/v1","ai_model":"test"})
    result,status=analyze(ITEM,settings)
    assert status=="fallback" and "地址无效" in result["limitations"][0]
