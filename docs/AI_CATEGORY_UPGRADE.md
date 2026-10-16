# v0.4.0：AI 独立领域与每栏 10 条

本次保留原有采集、摘要、影响分析、账号、搜索、收藏、历史和通知流程，新增 AI 人工智能领域。

| 新闻区域 | 时事政治 | 金融经济 | 科技发展 | AI 人工智能 |
|---|---:|---:|---:|---:|
| 中国新闻 | 最多 10 条 | 最多 10 条 | 最多 10 条 | 最多 10 条 |
| 国际新闻 | 最多 10 条 | 最多 10 条 | 最多 10 条 | 最多 10 条 |

合计最多 80 条。仍只使用指定日报时间窗内的有效新闻，按重要度、发布时间排序并去重。不足 10 条时显示实际数量，不使用旧新闻或虚构内容填满。

## 在现有 D 盘项目上升级

无需重新安装 Python 或 Node.js。

1. 在正在运行新闻服务的窗口按 **Ctrl+C**，等待 API、worker 和 Web 退出。
2. 将 `AI_News_AI_Upgrade.zip` **全部解压**到 D 盘，例如 `D:\AI-News-Upgrade`。不要在压缩包预览中运行。
3. 在解压后的 `AI-News-Upgrade` 文件夹双击 `01-update-news.cmd`。默认更新 `D:\AI-News-Setup\AI-News-Windows\AI-News`，使用 `D:\AI-News-Tools\Python312\python.exe`。
4. 脚本先检查全部文件、备份，再更新源码，设置 `MAX_PER_SECTION=10`，添加 AI 源并启动原有 D 盘启动器。
5. 网页打开后按 **Ctrl+F5** 刷新，登录后点击右上角 **更新早报**。生成完成后查看四个板块。

若项目在其他目录，在升级包解压目录打开 PowerShell，运行：

```powershell
& 'D:\AI-News-Tools\Python312\python.exe' '.\apply_upgrade.py' --project-root 'D:\你的目录\AI-News' --no-start
```

升级成功后使用该项目平时的启动方式。

## 数据与配置

- 不替换数据库、账号、收藏、私人标签和推送记录；本次不需要改动 SQLite 表结构。
- `.env` 只调整 `MAX_PER_SECTION`；模型地址、密钥和其他设置保留。自定义数据源保留；按 ID 补充缺失的 AI 源，已有同 ID 配置不覆盖。
- 所有改动前的文件保存在 `output/ai-upgrade-backup-日期-随机码/`，`restore.json` 记录原路径和校验值。此备份含 `.env` 时包含密钥，请保持私有。
- 校验失败、项目仍运行或检测到自定义源码时先停止升级，不覆盖该源码。文件写入异常会尝试恢复本次已修改文件。
- 已发布的历史日报与收藏快照保持原样。旧日报中的 AI 新闻仍保留当时的科技分类；新生成或手动重新生成的日报使用四类规则。
- 沿用 API 端口自动避让：8000 被占用时选择 8001–8099；网页仍为 `http://localhost:3000`。

## 分类与生成

AI 覆盖大模型、机器学习、AI 产品与应用、智能体、AI 安全与监管、AI 产业；以 AI 为主体的芯片、融资和政策也归 AI。一般芯片、软件、新能源、网络安全等仍归科技。每条新闻只进入一个领域。

规则预分类处理大小写和英文边界，避免把 airline、said 等含相似字母的词当作 AI；最终启用模型时使用模型分类。提示词缓存版本已更新，旧科技分析缓存不会直接阻止新的 AI 分类。规则与模型分类仍可能有误，需结合原文核对。

新增可配置 RSS：量子位 `https://www.qbitai.com/feed`、TechCrunch AI `https://techcrunch.com/category/artificial-intelligence/feed/`。中国/国际按新闻主体判断，不仅按媒体所在地；抓取失败在数据源页显示。原有源配置继续保留。

默认每格最多分析 20 个候选（`CANDIDATE_MULTIPLIER=2`），共最多 160 个；发布每格前 10 条。生成时间和模型调用量会比旧版增加。未配置模型时仍显示明确标注的来源摘要，不生成未经支持的影响预测。

## 源码 / Docker 用户

更新源码后，将现有 `.env` 中的 `MAX_PER_SECTION=3` 改为 `MAX_PER_SECTION=10`；备份后合并 `backend/sources.json` 的两个 AI 源。不要用 `.env.example` 覆盖现有密钥。执行 `docker compose up --build -d`，然后登录手动更新早报。

Android 源码已同步新增 AI 首页与搜索筛选；已安装 App 需要重新构建和安装新版 APK 才能看到新增栏目。本交付包不包含预编译 APK。
