"""四领域统一定义：API 和新闻分析流程共用，AI 与科技为独立类别。"""
from typing import Literal

Category = Literal["politics", "finance", "technology", "ai"]
CATEGORY_NAMES = {"politics": "政治", "finance": "金融", "technology": "科技", "ai": "AI 人工智能"}
CATEGORIES = tuple(CATEGORY_NAMES)
REGIONS = ("china", "international")
