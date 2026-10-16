import importlib.util, sqlite3
from pathlib import Path
from sqlalchemy import inspect, text
from app.db import make_session_factory


def test_old_database_upgrade_preserves_report_and_backup(tmp_path):
    path = Path(__file__).resolve().parents[1] / "migrations/versions/001_mvp.py"
    spec = importlib.util.spec_from_file_location("baseline", path)
    baseline = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(baseline)
    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as db:
        db.executescript(baseline.DDL)
        db.execute(
            "INSERT INTO daily_reports VALUES (42,'2026-10-12','2026-10-11 00:00:00','2026-10-12 00:00:00','2026-10-12 00:01:00','partial','{}','[]')"
        )
    factory = make_session_factory(f"sqlite:///{db_path}")
    with factory() as db:
        assert db.scalar(text("SELECT id FROM daily_reports")) == 42
        assert db.scalar(text("SELECT version_num FROM alembic_version")) == "003_push"
        assert {"users", "bookmarks", "devices", "notification_deliveries"} <= set(
            inspect(db.bind).get_table_names()
        )
    backups = list(tmp_path.glob("old.db.before_*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as db:
        assert db.execute("SELECT id FROM daily_reports").fetchone()[0] == 42
    make_session_factory(f"sqlite:///{db_path}")
    assert len(list(tmp_path.glob("old.db.before_*.bak"))) == 1
