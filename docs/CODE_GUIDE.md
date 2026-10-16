# 代码导读与功能定位

整理日期：2026-10-16。项目版本：v0.4.0。本说明用于区分 Web、App、共用服务与历史文档，并帮助在 GitHub 阅读源码。

## 先看哪里

1. [根 README](../README.md)：完整功能、运行方式和已知限制。
2. [Web 说明](../frontend/README.md)：网页启动、页面和接口调用位置。
3. [Android 说明](../mobile/README.md)：手机源码、构建、服务地址和通知接入。
4. [后端说明](../backend/README.md)：API、worker、数据库和配置。
5. [AI 模块说明](../ai-service/README.md)：分类、提示词和模型结果校验。

两端共享后端数据：手机和网页连接同一服务地址、登录同一账号时，可以读取同一收藏。每台电脑各自运行一个后端时，默认各有一个 SQLite 数据库，数据不会自行跨电脑同步。

## 从功能找到代码

| 需要查看的功能 | 主要文件 |
|---|---|
| Windows 启动与端口选择 | `start-windows.cmd`、`scripts/run_local.py` |
| API / worker 命令入口 | `manage.py` |
| 每天 08:00 开始生成 | `backend/app/clock.py`、`worker.py`、`jobs.py` |
| RSS 采集与清洗 | `backend/app/collector.py`、`feeds.py`、`sources.json` |
| AI 独立分类 | `ai-service/ai_service/taxonomy.py`、`classifier.py`、`prompt.py` |
| 每栏最多 10 条 | `.env.example` 的 `MAX_PER_SECTION`、`backend/app/config.py`、`pipeline.py` |
| 生成摘要与影响分析 | `ai-service/ai_service/analyzer.py`、`schemas.py` |
| Web 四领域展示 | `frontend/src/types.ts`、`pages/Dashboard.tsx`、`App.tsx` |
| App 四领域展示 | `mobile/lib/models/news.dart`、`screens/news_screens.dart`、`screens/search_screen.dart` |
| 账号和会话 | `backend/app/auth.py`、`frontend/src/auth.tsx`、`mobile/lib/state/news_controller.dart` |
| 收藏和标签 | `backend/app/collections.py`、`frontend/src/pages/Bookmarks.tsx`、`mobile/lib/screens/bookmarks_screen.dart` |
| 通知订阅与发送 | `backend/app/notifications.py`、`mobile/lib/services/push_service.dart` |
| SQLite 表结构与升级 | `database/schema.sql`、`backend/migrations/versions/` |

## 四领域的数量含义

| 区域 | 政治 | 金融 | 科技 | AI |
|---|---:|---:|---:|---:|
| 中国 | 最多 10 | 最多 10 | 最多 10 | 最多 10 |
| 国际 | 最多 10 | 最多 10 | 最多 10 | 最多 10 |

总计最多 80 条。新闻必须符合时间窗和筛选要求；实际不足时显示实际条数。更新源码不会改写历史日报和收藏快照，需要生成新版日报才能看到新栏目。手机已安装的旧 App 还需要重新构建并安装。

## GitHub 中的目录与自动检查

如果使用已有仓库，建议将完整项目放在 `AI-News/` 下。该目录内保留前端、App、共用后端、配置模板、依赖锁文件和文档，可以单独取出运行。

项目提供的 `.github/workflows/ci.yml` 适用于本项目处于仓库根目录的情况。放在子目录时，这份嵌套工作流不会自动运行。启用检查需要在仓库根 `.github/workflows/` 新增独立文件，并调整：

| 工作流项目 | 独立仓库 | `AI-News/` 子目录仓库 |
|---|---|---|
| 后端工作目录 | 仓库根 | `AI-News` |
| pip 缓存依赖路径 | `backend/requirements.txt` | `AI-News/backend/requirements.txt` |
| Web 工作目录 | `frontend` | `AI-News/frontend` |
| npm 缓存依赖路径 | `frontend/package-lock.json` | `AI-News/frontend/package-lock.json` |
| App 工作目录 | `mobile` | `AI-News/mobile` |
| APK 上传路径 | `mobile/build/app/outputs/flutter-apk/app-debug.apk` | `AI-News/mobile/build/app/outputs/flutter-apk/app-debug.apk` |

其他项目的工作流应保留。Android 工作流只有在工具链可获取、检查和原生构建成功后才会产出 APK；代码上传成功不代表 App 已构建成功。

## 本次标注与验证范围

本次 GitHub 整理增加目录说明、关键入口注释，修正 App 文档版本，并区分源码、增量升级包和安装包；未改变业务功能。

v0.4.0 此前通过 68 项后端/升级测试、6 项 Web 测试和 Web 生产构建，记录见 [当前测试报告](AI_CATEGORY_TEST_REPORT.md)。本次文档和注释整理不重复执行整套业务测试。Flutter 新版测试、APK 构建、手机推送及 Windows 实机验收仍待完成。Phase 1 及 Phase 2/3 测试文档用于保留历史，不代表这些检查已在当前版本重跑。

GitHub 源码不包含真实 `.env`、数据库、私有密钥、Android 签名、Python/Node.js 安装器、`.venv`、`node_modules` 或构建输出。
