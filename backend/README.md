# 共用后端：FastAPI + SQLite

Web 与 Android App 连接同一个后端。API 提供日报读取、账号、搜索、收藏、标签和设备通知接口；独立 worker 负责滚动采集、北京时间 08:00 开始生成日报，以及处理通知队列。

## 启动位置

以下命令从 [项目根目录](../README.md) 执行，不是在 `backend` 内执行。Windows 一键启动可直接双击根目录 `start-windows.cmd`。

手动启动时，首次准备环境：

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe manage.py api
```

另开一个同目录 PowerShell 运行 worker：

```powershell
.\.venv\Scripts\python.exe manage.py worker
```

API 默认 `http://localhost:8000`，接口说明 `/docs`，健康检查 `/api/v1/health`。只启动 API 可以读取已有数据；自动生成和通知需要 worker 同时运行。Web 启动见 [前端指南](../frontend/README.md)。

## 文件标注

| 模块 | 职责 |
|---|---|
| `app/main.py` | API 装配、健康状态、日报、新闻详情与任务入口 |
| `app/config.py` | 从根 `.env` 读取配置；每栏数量默认 10 |
| `app/auth.py` | 账号、密码哈希、Cookie / Bearer 会话和撤销 |
| `app/collections.py` | 搜索、收藏快照与私人标签 |
| `app/notifications.py` | 推送订阅、通知队列和极光服务适配 |
| `app/worker.py` / `app/jobs.py` | 单实例 worker 与任务状态 |
| `app/collector.py` / `app/feeds.py` | 滚动采集、RSS 解析和摘要清洗 |
| `app/pipeline.py` | 去重、候选筛选、调用 AI、排名和日报事务发布 |
| `app/reports.py` | 日报结构与 Markdown 导出 |
| `app/models.py` / `app/user_models.py` | SQLAlchemy 新闻、账号与通知模型 |
| `app/db.py` / `app/migrations.py` | 数据库连接、备份和迁移执行 |
| `migrations/versions/` | 001 新闻、002 用户、003 推送迁移 |
| `sources.json` | 新闻来源配置，可按实际网络情况调整 |
| `tests/` | API、隔离、采集、分类、通知、迁移与升级回归 |

## 数据与模型设置

默认数据库为根目录 `database/data/news.db`，不包含在 GitHub 源码中。真实 `.env`、账号数据、模型密钥、推送 Master Secret 也不提交。配置字段参考根 [.env.example](../.env.example)。

模型分析代码在 [ai-service](../ai-service/README.md)，由 Python 进程直接导入，无需再启动一个 HTTP 服务。未启用模型或分析失败时显示有标注的来源摘要。

更新已有安装时保留 `.env`、数据库与自定义来源。v0.4.0 需要 `MAX_PER_SECTION=10` 并合并 AI 来源；操作见 [升级说明](../docs/AI_CATEGORY_UPGRADE.md)。

## 测试

在根目录安装开发依赖后执行：

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

本版此前后端与升级测试 68 项通过，实际覆盖和未验证项见 [测试报告](../docs/AI_CATEGORY_TEST_REPORT.md)。
