# Database

默认数据库：本机 `database/data/news.db`；Compose 为 `news_data` 卷内 `/data/news.db`。

表定义见 `backend/app/models.py`；生成的 SQLite DDL 见 `schema.sql`。时间使用 UTC 无偏移的数据库值，API 输出统一添加 `+00:00`。

SQLite 已设置 WAL、外键检查与 30 秒 busy timeout。API 与 worker 共用本机持久卷，不支持多个 worker 或网络共享盘。

`create_all` 只用于首次建表。后续结构升级要先备份，再采用 Alembic 等正式迁移流程。PostgreSQL 迁移需执行兼容性与完整性测试。

备份时推荐停服务后复制整个数据目录，或使用 Python sqlite3 的在线 backup API（不要在写入中仅复制 news.db 而漏掉 WAL）。不要将 `.db`、API 密钥或个人收藏上传至 GitHub。
