# Windows 本机启动：Python + Node.js

适用于 AI Daily News Assistant v0.4.0，包含账号、搜索、收藏及 Android 源码。本说明启动的是电脑上的 Web 服务，Android APK 仍需单独构建。

不需要 Docker、WSL、Redis 或单独安装数据库。需要安装 Python 和 Node.js，首次下载项目依赖需要联网。启动程序不会读取或修改 Windows 系统配置。

## 1. 安装两个运行环境

| 软件 | 此项目使用的版本 | 官方下载和选择 |
|---|---|---|
| Python | 3.12.x，64 位 | [Python 3.12.10 下载页](https://www.python.org/downloads/release/python-31210/)，页面 Files 中选择 **Windows installer (64-bit)** |
| Node.js | 24.x LTS，至少 24.15.0 | [Node.js 下载页](https://nodejs.org/en/download)，选择 **24 LTS、Windows、x64、Windows Installer (.msi)** |

Python 安装时保留 pip、venv 和 Python Launcher（py），勾选 **Add python.exe to PATH**。Python 3.12.10 是 3.12 系列最后一个提供传统 Windows 安装器的维护版本，并非 Python 的最新安全修复版；已有较新 3.12 运行时可以直接使用。后续更换 Python 主版本需要重新验证依赖。

Node.js 按默认选项安装，保留 npm 和 Add to PATH。这份启动器固定使用 24.x LTS，与项目验证的版本系列一致。

安装结束后关闭之前的终端，重新打开 PowerShell，检查：

```powershell
py -3.12 --version
node --version
npm.cmd --version
```

应分别看到 `Python 3.12.x`、`v24.x.x`（至少 `v24.15.0`）及 npm 版本。这里用 `npm.cmd`，避免 PowerShell 拦截同名的 `npm.ps1`。无需更改系统执行策略。

## 2. 解压并启动

1. 将更新后的项目压缩包完整解压到本地，例如 `D:\AI-News`。找到包含 `manage.py`、`backend`、`frontend` 和 `start-windows.cmd` 的文件夹。
2. 双击 **start-windows.cmd**。无需管理员权限。
3. 第一次启动会自动创建 `.venv`，安装 Python 和网页依赖，并在 `.env` 不存在时复制配置模板。它会保留已有 `.env` 和数据库。
4. 接着启动 API、定时任务 worker 和网页服务，并检查它们是否可用。
5. 看到 `READY: http://localhost:3000` 后会自动打开网页。没有自动打开时，手动访问 [http://localhost:3000](http://localhost:3000)。

API 默认尝试 8000 端口。如果它被 Windows System（PID 4）或其他程序占用，启动器会在 8000–8099 范围内选择空闲端口，并同步网页代理与健康检查地址。窗口会显示实际 `API address`，浏览器仍然访问 `http://localhost:3000`。此过程不会结束占用端口的程序，也不修改 Windows 系统服务。

以后仍然双击同一个文件。依赖和版本未变时会复用已安装内容。启动窗口需要保持开启，停止时在该窗口按 **Ctrl+C**。如果 cmd 随后询问是否终止批处理，按 `Y` 回车。

窗口中的 `Installing ... dependencies` 表示正在下载依赖，还没有启动完成。下载出错时不会继续假装启动成功；保留窗口中的错误信息。

已有项目升级：把压缩包解压到一个临时目录，将更新后的源码复制到原项目目录，保留原 `.env`、`database/data` 和自定义 `backend/sources.json`。不要将整个旧目录删除后覆盖。新包不包含任何用户数据。

## 3. 打开网页之后

在“我的账号”注册并登录，再到首页点击“更新早报”。worker 也会按北京时间每天 08:00 开始生成；电脑、网络和启动窗口必须保持运行。首次运行时间已过 08:00 时，会尝试补跑当前一期。

未配置模型时显示来源摘要，不生成 AI 影响分析。需要 AI 时，用记事本打开项目根目录 `.env`，填入自己供应商的有效 `AI_BASE_URL`、`AI_API_KEY` 和 `AI_MODEL`。基础 URL 使用供应商规定的 `/v1` 等接口前缀，不要填完整 `/chat/completions` 地址。保存后按 Ctrl+C 停止，重新双击启动器，然后更新日报。

数据默认保存在 `database/data/news.db`。来源能否访问、是否有截止时间前的新闻，取决于你电脑的网络和来源内容；网页能打开不等于日报已经生成。

## 4. 遇到问题

| 提示或现象 | 处理方式 |
|---|---|
| `Python 3.12 was not found` | 安装 Python 3.12 和 Python Launcher 后重新双击；已安装其他 Python 版本无需卸载 |
| `Install Node.js 24 LTS` | 安装 Node 24.x LTS（至少 24.15），关闭旧窗口后重新启动 |
| `Port 3000 is unavailable` | 网页端口被占用；检查之前的项目窗口或其他应用 |
| `No available API port` | 8000–8099 均不可绑定；检查本机端口占用或系统保留范围。不要结束 System 进程 |
| `launcher is already running` | 项目已经有启动窗口，不要重复双击，打开现有窗口或网页 |
| `pip` / `npm` 下载超时或失败 | 把错误截图发来，排查网络或代理。不要发送 `.env` 或 API 密钥 |
| `.venv` 不完整或 Python 版本不同 | 将 `.venv` 改名为 `.venv-backup`，重新运行启动器；数据库不在虚拟环境里 |
| `Startup timed out` / 服务退出 | 查看 `output/local-run/api.log`、`worker.log` 或 `web.log` 中对应的错误 |
| 网页可用但新闻没有生成 | 查看页面的新闻来源和任务状态，以及 `worker.log`；保持窗口运行，确认来源可访问 |

依赖损坏时，先停止运行中的项目，再在项目目录执行：

```powershell
py -3.12 scripts\run_local.py --repair
```

查看最近的日志（在含 `manage.py` 的目录执行）：

```powershell
Get-Content .\output\local-run\api.log -Tail 40
Get-Content .\output\local-run\worker.log -Tail 40
Get-Content .\output\local-run\web.log -Tail 40
```

## 5. 不用启动脚本：手动启动

在资源管理器打开含 `manage.py` 的项目目录，在地址栏输入 `powershell` 后按 Enter。第一个窗口运行：

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe manage.py api
```

第一个窗口保持开启，再从同一个项目目录打开第二个 PowerShell：

```powershell
.\.venv\Scripts\python.exe manage.py worker
```

从同一个项目目录打开第三个 PowerShell：

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev -- --strictPort
```

打开 [http://localhost:3000](http://localhost:3000)。需要停止时，在三个窗口分别按 Ctrl+C。手动方式与启动器方式选一种使用，不能同时占用相同端口。

## 验证范围

2026-10-15 端口修复回归：在 Linux 环境实际占用 8000 和 8001，启动器选择 8002；API 与网页代理健康接口均返回 200，worker 在线，网页内容可访问。原占用端口的监听器继续工作，停止项目后释放 8002 和 3000，保留 `.env` 与数据库。默认端口空闲和候选范围耗尽也已检查。该测试未在用户 Windows 上执行。

2026-10-14 在 Linux 环境使用 Python 3.12.14、Node 24.19.0 验证：首次安装依赖并启动成功；API 与网页代理健康接口返回 200，worker 在线；网页和前端入口可访问；连续两轮启动/停止、依赖复用、拒绝重复启动、端口占用提示、保留 `.env` 与数据库均通过。

Windows 的 `.cmd` 入口、安装器、进程停止和浏览器自动打开需在你的电脑上确认。本次没有远程操作你的 Windows 电脑，也没有在本次启动检查中验证真实 AI 账号或 Android 推送。


已有 D 盘项目从三类、每栏 3 条升级为四类、每栏 10 条，请先按 [AI 板块升级说明](AI_CATEGORY_UPGRADE.md) 使用小型升级包，保留现有配置和数据。
