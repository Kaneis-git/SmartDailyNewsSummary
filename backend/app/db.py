import json
from pathlib import Path
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel, HttpUrl
from typing import Literal
from .models import Source
from .migrations import migrate
from ai_service.taxonomy import Category


class SourceConfig(BaseModel):
    id: str
    name: str
    feed_url: HttpUrl
    region_hint: Literal["china", "international"]
    category_hint: Category | Literal["mixed"]
    enabled: bool = True


def make_session_factory(db_url):
    engine = create_engine(db_url, connect_args={"check_same_thread": False, "timeout": 30})

    @event.listens_for(engine, "connect")
    def sqlite_options(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
        dbapi_conn.execute("PRAGMA busy_timeout=30000")
        dbapi_conn.execute("PRAGMA journal_mode=WAL")

    migrate(engine)
    return sessionmaker(engine, expire_on_commit=False)


def sync_sources(factory, config_path: Path):
    configs = [SourceConfig.model_validate(item) for item in json.loads(config_path.read_text(encoding="utf-8"))]
    if len({c.id for c in configs}) != len(configs):
        raise ValueError("新闻来源 ID 不可重复")
    with factory.begin() as session:
        for old in session.scalars(select(Source)):
            old.enabled = False
        for config in configs:
            if config.feed_url.scheme != "https":
                raise ValueError("新闻源须使用 HTTPS")
            session.merge(Source(**config.model_dump(mode="json")))
