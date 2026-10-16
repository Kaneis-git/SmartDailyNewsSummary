from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from .taxonomy import Category


class Analysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline: str = Field(min_length=1, max_length=250)
    region: Literal["china", "international"]
    category: Category | Literal["other"]
    summary: str = Field(min_length=1, max_length=1200)
    facts: list[str] = Field(default_factory=list, max_length=5)
    importance: int = Field(ge=1, le=5, strict=True)
    importance_reason: str = Field(max_length=600)
    why_important: str = Field(default="", max_length=800)
    people_impact: str = Field(default="", max_length=800)
    market_impact: str = Field(default="", max_length=800)
    short_term: str = Field(default="", max_length=800)
    long_term: str = Field(default="", max_length=800)
    industries: list[str] = Field(default_factory=list, max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=8)
    limitations: list[str] = Field(default_factory=list, max_length=5)
