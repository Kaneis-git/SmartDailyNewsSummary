import re

KEYWORDS = {
    "technology": ("芯片", "网络安全", "半导体", "科技", "软件", "新能源", "量子", "航天", "机器人", "chip", "software", "cyber", "technology", "semiconductor", "spacex"),
    "finance": ("金融", "经济", "利率", "货币", "股票", "外汇", "央行", "财政", "投资", "关税", "债券", "制造业", "通胀", "econom", "inflation", "rate", "bank", "market", "tariff", "trade", "oil", "finance"),
    "politics": ("政治", "外交", "政府", "国务院", "政策", "选举", "总统", "总理", "人大", "联合国", "议会", "战争", "停火", "会谈", "minister", "election", "president", "government", "parliament", "war", "ceasefire", "diplomat", "policy"),
}
EXCLUDED = ("足球", "篮球", "娱乐", "影星", "明星", "体育", "football", "celebrity", "cricket", "tennis")

# ASCII boundaries also match "AI芯片" without matching "airline" or "said".
AI_PATTERN = re.compile(
    r"(?<![a-z0-9])(?:ai|aigc|llms?|openai|anthropic|deepseek|qwen|"
    r"(?:chat)?gpt(?:[- ]?\d[\w.-]*)?|artificial intelligence|machine learning|"
    r"deep learning|large language models?|neural networks?)(?![a-z0-9])",
    re.IGNORECASE,
)
AI_TERMS = ("人工智能", "大模型", "机器学习", "深度学习", "神经网络", "生成式智能", "智能体", "通义千问", "智谱", "月之暗面", "文心一言", "豆包")
AI_MODEL_PATTERN = re.compile(r"(?<![a-z0-9])(?:claude|gemini|llama|kimi|agents?|agentic)(?![a-z0-9])", re.IGNORECASE)


def is_ai_topic(text, hint="mixed"):
    explicit = bool(AI_PATTERN.search(text)) or any(word in text for word in AI_TERMS)
    # Ambiguous names such as Gemini/Agent need AI-source or model context.
    model_context = hint == "ai" or any(contains(text, word) for word in
        ("模型", "智能化", "聊天机器人", "model", "chatbot", "assistant", "autonomous"))
    return explicit or bool(AI_MODEL_PATTERN.search(text) and model_context)


def contains(text, word):
    if word.isascii():
        return bool(re.search(r"\b" + re.escape(word) + r"\w*\b", text))
    return word in text


def classify(item):
    text = (item["title"] + " " + item["text_excerpt"]).casefold()
    scores = {category: sum(contains(text, word) for word in words) for category, words in KEYWORDS.items()}
    category = max(scores, key=scores.get)
    if is_ai_topic(text, item["category_hint"]):
        category = "ai"
    elif not scores[category]:
        if item["category_hint"] in ("finance", "technology", "ai") and not any(contains(text, w) for w in EXCLUDED):
            category = item["category_hint"]
        else:
            category = "other"
    elif any(contains(text, w) for w in EXCLUDED) and scores[category] < 2:
        category = "other"
    china_terms = ("中国", "中国人民银行", "国务院", "华为", "腾讯", "阿里巴巴", "比亚迪", "小米", "智谱", "月之暗面", "通义千问", "文心一言", "豆包", "china", "chinese", "huawei", "tencent", "byd", "xiaomi", "deepseek", "qwen")
    foreign_terms = ("美国", "美联储", "美股", "日本", "英国", "欧盟", "欧洲央行", "俄罗斯", "以色列", "加沙", "韩国", "谷歌", "英伟达", "微软", "germany", "japan", "russia", "united states", "united kingdom", "federal reserve", "openai", "anthropic", "google", "nvidia", "microsoft")
    if any(contains(text, word) for word in china_terms):
        region = "china"
    elif any(contains(text, word) for word in foreign_terms):
        region = "international"
    else:
        region = item["region_hint"]
    importance = min(4, 2 + int(any(contains(text, w) for w in ("央行", "国务院", "关税", "战争", "ceasefire", "central bank", "breakthrough"))) + int(max(scores.values()) >= 4))
    return region, category, importance
