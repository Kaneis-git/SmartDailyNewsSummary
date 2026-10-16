from pathlib import Path
from datetime import datetime, UTC
import sqlite3
from alembic import command
from alembic.config import Config
from filelock import FileLock
from sqlalchemy import inspect, text

HEAD = "003_push"


def migrate(engine):
    path = Path(engine.url.database)
    path.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(path) + ".migration.lock", timeout=60):
        with engine.connect() as conn:
            tables = inspect(conn).get_table_names()
            current = (
                conn.scalar(text("SELECT version_num FROM alembic_version"))
                if "alembic_version" in tables
                else None
            )
        if current == HEAD:
            return
        if "daily_reports" in tables:
            backup = path.with_name(
                path.name
                + ".before_"
                + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
                + ".bak"
            )
            with sqlite3.connect(path) as original, sqlite3.connect(backup) as target:
                original.backup(target)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
