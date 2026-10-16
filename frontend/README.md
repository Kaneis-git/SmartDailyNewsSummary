# Web 版：React + TypeScript

这是智能每日新闻总结助手的网页客户端。提供今日早报、历史、新闻详情、来源状态、中文搜索、账号、收藏和私人标签。中国/国际各包含政治、金融、科技、AI 四个板块；服务器每栏最多返回 10 条，页面展示实际数量。

## 如何启动

Windows 用户先回到 [项目根目录](../README.md)，双击 `start-windows.cmd`，由启动器统一运行 API、worker 和 Web。需要 Python 3.12 与 Node.js 24.x（至少 24.15）。完整步骤见 [Windows 启动指南](../docs/WINDOWS_LOCAL_START.md)。

已有后端运行时，可在本目录单独启动 Web：

```powershell
npm.cmd ci
npm.cmd run dev -- --strictPort
```

浏览器访问 `http://localhost:3000`。页面通过 `/api/v1` 请求后端；Vite 默认转发到 `http://127.0.0.1:8000`。统一启动器会同步所选 API 端口。手动使用其他 API 端口时，先在同一个 PowerShell 设置 `$env:AI_NEWS_API_TARGET='http://127.0.0.1:8001'`，再启动 Web。

## 文件标注

| 文件或目录 | 作用 |
|---|---|
| `src/main.tsx` | 浏览器入口，装配路由与账号状态 |
| `src/App.tsx` | 页面导航和公共布局 |
| `src/api.ts` | 后端请求与错误处理 |
| `src/auth.tsx` | 注册、登录、退出和当前用户状态 |
| `src/state.tsx` | 日报与运行状态 |
| `src/types.ts` | API 数据和四领域类型定义 |
| `src/pages/Dashboard.tsx` | 日报展示、区域与领域筛选 |
| `src/pages/Search.tsx` | 标题/摘要搜索与筛选 |
| `src/pages/Bookmarks.tsx` | 收藏和私人标签管理 |
| `src/components/` | 新闻卡片、收藏按钮等复用组件 |
| `src/tests/` | 账号交互和四领域展示测试 |
| `vite.config.ts` / `nginx.conf` | 开发代理 / Docker Web 反向代理 |

## 构建与验证

```powershell
npm.cmd test
npm.cmd run build
```

生产静态文件输出到 `dist/`。`dist`、`node_modules` 不提交 Git。单独托管这些静态文件仍需要可访问的后端、数据库和 worker；上传 GitHub 不会自动运行新闻服务。

本版此前验证为 6 项 Web 测试通过、生产构建通过，详见 [测试报告](../docs/AI_CATEGORY_TEST_REPORT.md)。
