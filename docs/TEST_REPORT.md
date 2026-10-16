# v0.3.0 · Phase 2 / Phase 3 测试报告

2026-10-13，Linux、Python 3.12、Node 24.19.0、Flutter 3.47.7 / Dart 3.13.5。测试在恢复后的最终源码上重新执行。Phase 1 历史真实采集记录保存在 PHASE_1_TEST_REPORT.md，不作为本轮连通性验证。

## 实际结果

| 命令/检查 | 结果 | 证明范围 |
|---|---|---|
| 根目录 `python -m pytest -q` | **41 项通过** | 原有回归 30；账号/收藏/搜索 5；通知 5；迁移 1 |
| frontend `npm test` | **4 项通过** | 游客、注册退出、收藏入口、中文搜索 |
| frontend `npm run build` | **通过** | TypeScript 与 Vite 构建，JS 294.51 kB / gzip 94.07 kB |
| mobile `flutter analyze --no-pub` | **通过，无问题** | Flutter/Dart 静态检查 |
| mobile `flutter test --no-pub --reporter expanded` | **15 项通过** | 控制器/API/缓存 10；界面 5 |
| SQLite 参考 DDL | **通过，15 张业务表** | 在空 SQLite 实际执行建表 |
| Compose / CI YAML | **解析与关键字段检查通过** | API/worker 推送环境变量与三组 CI 任务；不是 Docker/远端执行 |
| `flutter build apk --debug --no-pub` | **未完成：缺 Android SDK** | 返回 No Android SDK found，没有 APK |

后端有一条 Starlette TestClient 对 httpx 的弃用提示，未影响结果；后续依赖升级需评估迁移。npm 的 http-proxy 配置提示来自当前执行环境。

## 关键覆盖

- Cookie/Origin、密码与令牌哈希、会话过期/撤销/密码变更、登录限流。
- 两用户收藏/标签隔离、重复收藏幂等、收藏快照不受日报改写影响。
- 中文搜索、区域/日期/分页、LIKE 字符转义；旧库主键保留、备份和迁移幂等。
- 同设备/日期通知唯一、登记刷新、空/失败报告不推送、关闭开关、接受回执、429/超时、退订和进程恢复、跨账号设备绑定。
- Flutter API 中文解析/Bearer/不重定向；安全存储与退出清理；旧请求不恢复退出数据、旧 401 不覆盖新会话。
- 7 期缓存上限、服务器隔离、网络回退、404 不回退；有效通知日期和北京时间，游客/表单/空日报/离线/搜索界面。

新闻与账号使用合成 fixtures，模型和推送使用模拟网络。没有调用收费模型、发送真实消息或使用生产密钥。单元/组件测试不覆盖 Gradle/Kotlin/原生插件编译，也不代表设备已展示通知。

## 尚未验收

| 项目 | 原因与下一步 |
|---|---|
| Android APK / 原生编译 | 当前无 Android SDK；按 mobile/README 配置工具链后构建 |
| 真机推送 / 冷启动 | 需用户极光项目、匹配 AppKey、设备与签名；分别核对 accepted 和设备展示 |
| 国内厂商离线通道 | 当前仅基础极光；按目标机型配置厂商通道并实测 |
| Windows Docker | 当前无 Docker CLI，未在 Windows 运行；本地按 README 验收 |
| 真实模型/来源 | 本轮没重做真实 RSS 或模型调用；用户网络下核对覆盖、准确性和费用 |
| 浏览器视觉/读屏 | 完成组件测试与构建，没有截图、读屏和真机屏幕验收 |
| GitHub Actions | 工作流已提供，尚未远端执行或取得 APK artifact |
| 长期定时运行 | 没有实际连续等到次日 08:00；需常开主机观察生成、恢复和重复提醒 |

## 用户环境验收

1. 备份并保留原 .env、sources.json、数据卷，启动 Compose，核对历史日报和 worker 心跳。
2. 两账号测试隔离，同账号 Web/App 测试收藏与标签同步。
3. 构建并安装 debug APK，核对服务地址、登录、日报、详情、历史、搜索和收藏。
4. 读取几期后断网，确认离线标识；切换账号/服务不能显示原私有数据。
5. 同意通知并授权，生成非空日报；核对 provider 记录和手机展示，点击打开正确日期。
6. 重跑同一期不重复入队；退出、关权限、改密码后检查后续通知停止。
7. 核对前后台、冷启动、强制停止、省电、重启与网络切换；配置需要的厂商通道。
8. 正式发布前使用自己的 release 签名与 HTTPS，debug 不作为商店正式包。

未执行的验收不标记为通过。构建、升级、签名与配置命令均在根 README 和 mobile/README。
