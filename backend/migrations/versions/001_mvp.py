from alembic import op
from sqlalchemy import inspect

revision = "001_mvp"
down_revision = None
branch_labels = None
depends_on = None
DDL = '-- SQLite initial schema; authoritative models: backend/app/models.py\n-- Not an upgrade migration.\n\n\nCREATE TABLE daily_reports (\n\tid INTEGER NOT NULL, \n\treport_date DATE NOT NULL, \n\twindow_start DATETIME NOT NULL, \n\twindow_end DATETIME NOT NULL, \n\tgenerated_at DATETIME NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tcoverage JSON NOT NULL, \n\tsource_results JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (report_date)\n)\n\n;\n\nCREATE TABLE job_runs (\n\tid VARCHAR(36) NOT NULL, \n\treport_date DATE NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tactive_slot INTEGER, \n\tcreated_at DATETIME NOT NULL, \n\tstarted_at DATETIME, \n\tfinished_at DATETIME, \n\tmessage TEXT NOT NULL, \n\tsource_results JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (active_slot)\n)\n\n;\nCREATE INDEX ix_job_runs_report_date ON job_runs (report_date);\n\nCREATE TABLE runtime_state (\n\t"key" VARCHAR(80) NOT NULL, \n\tvalue TEXT NOT NULL, \n\tPRIMARY KEY ("key")\n)\n\n;\n\nCREATE TABLE sources (\n\tid VARCHAR(80) NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\tfeed_url TEXT NOT NULL, \n\tregion_hint VARCHAR(20) NOT NULL, \n\tcategory_hint VARCHAR(20) NOT NULL, \n\tenabled BOOLEAN NOT NULL, \n\tPRIMARY KEY (id)\n)\n\n;\n\nCREATE TABLE news (\n\tid INTEGER NOT NULL, \n\tsource_id VARCHAR(80) NOT NULL, \n\ttitle TEXT NOT NULL, \n\turl TEXT NOT NULL, \n\turl_hash VARCHAR(64) NOT NULL, \n\ttext_excerpt TEXT NOT NULL, \n\tcontent_hash VARCHAR(64) NOT NULL, \n\tpublished_at DATETIME NOT NULL, \n\tfetched_at DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(source_id) REFERENCES sources (id), \n\tUNIQUE (url_hash)\n)\n\n;\nCREATE INDEX ix_news_published_at ON news (published_at);\n\nCREATE TABLE news_analyses (\n\tid INTEGER NOT NULL, \n\tnews_id INTEGER NOT NULL, \n\tcontent_hash VARCHAR(64) NOT NULL, \n\tmodel VARCHAR(200) NOT NULL, \n\tprompt_version VARCHAR(80) NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tpayload JSON NOT NULL, \n\tcreated_at DATETIME NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (news_id, content_hash, model, prompt_version), \n\tFOREIGN KEY(news_id) REFERENCES news (id)\n)\n\n;\nCREATE INDEX ix_news_analyses_news_id ON news_analyses (news_id);\n\nCREATE TABLE report_items (\n\tid INTEGER NOT NULL, \n\treport_id INTEGER NOT NULL, \n\tnews_id INTEGER NOT NULL, \n\tanalysis_id INTEGER NOT NULL, \n\tposition INTEGER NOT NULL, \n\tregion VARCHAR(20) NOT NULL, \n\tcategory VARCHAR(20) NOT NULL, \n\tsnapshot JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (report_id, news_id), \n\tFOREIGN KEY(report_id) REFERENCES daily_reports (id), \n\tFOREIGN KEY(news_id) REFERENCES news (id), \n\tFOREIGN KEY(analysis_id) REFERENCES news_analyses (id)\n)\n\n;\nCREATE INDEX ix_report_items_report_id ON report_items (report_id);\n'
EXPECTED = {
    "daily_reports": [
        "coverage",
        "generated_at",
        "id",
        "report_date",
        "source_results",
        "status",
        "window_end",
        "window_start",
    ],
    "job_runs": [
        "active_slot",
        "created_at",
        "finished_at",
        "id",
        "message",
        "report_date",
        "source_results",
        "started_at",
        "status",
    ],
    "runtime_state": ["key", "value"],
    "sources": ["category_hint", "enabled", "feed_url", "id", "name", "region_hint"],
    "news": [
        "content_hash",
        "fetched_at",
        "id",
        "published_at",
        "source_id",
        "text_excerpt",
        "title",
        "url",
        "url_hash",
    ],
    "news_analyses": [
        "content_hash",
        "created_at",
        "id",
        "model",
        "news_id",
        "payload",
        "prompt_version",
        "status",
    ],
    "report_items": [
        "analysis_id",
        "category",
        "id",
        "news_id",
        "position",
        "region",
        "report_id",
        "snapshot",
    ],
}


def upgrade():
    inspector = inspect(op.get_bind())
    tables = set(inspector.get_table_names()) - {"alembic_version"}
    if tables:
        if not set(EXPECTED) <= tables:
            raise RuntimeError("数据库结构不符合 Phase 1，请先备份并检查")
        for name, columns in EXPECTED.items():
            if sorted(c["name"] for c in inspector.get_columns(name)) != columns:
                raise RuntimeError("旧表结构已改变：" + name)
        return
    sql = "\n".join(
        line for line in DDL.splitlines() if not line.lstrip().startswith("--")
    )
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    raise RuntimeError("请从升级前备份恢复，不自动删除表")
