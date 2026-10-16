import json
import time
from urllib.parse import urlsplit
import httpx
from pydantic import ValidationError
from .classifier import classify
from .prompt import SYSTEM_PROMPT
from .schemas import Analysis
from .taxonomy import CATEGORY_NAMES


def extractive(item, reason="未配置模型，展示来源摘要；影响分析未生成"):
    region, category, importance = classify(item)
    return Analysis(headline=item["title"][:250], region=region, category=category,
                    summary=(item["text_excerpt"] or "来源仅提供标题，暂无原文摘要。")[:1000],
                    importance=importance, importance_reason="按主题关键词进行规则排序，未经过模型判断。",
                    tags=[{**CATEGORY_NAMES, "other": "其他"}[category]],
                    limitations=[reason, "输入限于该来源 RSS 摘要；请阅读原文核对完整背景。"])


def analyze(item, settings, transport=None):
    if not settings.ai_enabled:
        return extractive(item).model_dump(), "extractive"
    if len(item["text_excerpt"]) < 30:
        return extractive(item, "来源摘要过短，暂不生成影响推断。").model_dump(), "fallback"
    base = settings.ai_base_url.rstrip("/")
    parsed = urlsplit(base)
    local_http = parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "host.docker.internal")
    if not parsed.hostname or parsed.username or parsed.password or not (parsed.scheme == "https" or local_http):
        return extractive(item, "模型地址无效；远程接口须使用 HTTPS。").model_dump(), "fallback"
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"} if settings.ai_api_key else {}
    payload = {"model": settings.ai_model, "temperature": 0.2, "max_tokens": 2200,
               "messages": [{"role": "system", "content": SYSTEM_PROMPT + "\nSchema:" + json.dumps(Analysis.model_json_schema(), ensure_ascii=False)},
                            {"role": "user", "content": json.dumps({"title": item["title"], "source_text": item["text_excerpt"], "source_name": item["source_name"]}, ensure_ascii=False)}]}
    reason = "模型暂时不可用，已保留来源摘要。"
    with httpx.Client(timeout=settings.ai_timeout, transport=transport) as client:
        for attempt in range(2):
            try:
                response = client.post(base + "/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                raw = response.json()["choices"][0]["message"]["content"]
                if not isinstance(raw, str) or len(raw) > 24000:
                    raise ValueError("输出格式或长度不符")
                result = Analysis.model_validate_json(raw)
                return result.model_dump(), "ai"
            except httpx.HTTPStatusError as exc:
                reason = f"模型请求失败（HTTP {exc.response.status_code}），已保留来源摘要。"
                if exc.response.status_code < 500 and exc.response.status_code != 429:
                    break
            except (httpx.RequestError, ValidationError, ValueError, KeyError, IndexError, TypeError):
                reason = "模型超时或输出未通过结构校验，已保留来源摘要。"
            if attempt == 0:
                time.sleep(0.5)
    return extractive(item, reason).model_dump(), "fallback"
