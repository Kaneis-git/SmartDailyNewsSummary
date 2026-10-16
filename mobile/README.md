# App 版：Android 客户端 · v0.4.0

完整 Flutter 源码，支持 Android 7.0 / API 24+。当前没有 APK；Flutter 单元/组件检查不等于 Gradle/Kotlin/插件原生编译和真机验收。

本目录是手机 App，与 [Web 版](../frontend/README.md) 共用 [后端](../backend/README.md)。先启动后端和网页服务，再配置手机的 API 地址。以下命令从 `mobile` 目录执行。

| 位置 | 中文标注 |
|---|---|
| `lib/main.dart` | App 启动入口，恢复服务地址、创建存储和状态对象 |
| `lib/app.dart` | 应用外壳与导航 |
| `lib/screens/` | 今日、历史、详情、搜索、收藏、账号和设置页面 |
| `lib/services/` | HTTP 接口、安全存储、公共日报缓存与推送服务 |
| `lib/state/news_controller.dart` | 页面共享状态、登录、日报加载和收藏操作 |
| `lib/models/news.dart` | 新闻、日报与分类数据模型 |
| `android/` | Android 权限、Gradle 构建和签名配置 |
| `test/` | Flutter 单元与组件测试 |

## Windows 环境

安装 Flutter 3.47.7、JDK 17、Android Studio。SDK Manager 安装 Platform 36、Build-Tools、Platform-Tools、Command-line Tools 和 NDK 28.2.13676358；自行阅读并接受所需许可。

```powershell
flutter doctor -v
flutter pub get --enforce-lockfile
flutter analyze
flutter test
flutter run
flutter build apk --debug
```

SDK 未发现时，使用 `flutter config --android-sdk "C:\Users\你的用户名\AppData\Local\Android\Sdk"`。国内网络可参考 [Flutter 官方中国网络指南](https://docs.flutter.dev/community/china)。

APK 成功后在 `build/app/outputs/flutter-apk/app-debug.apk`。模拟器默认访问电脑 `http://10.0.2.2:3000/api/v1`。真机按根 README 配置局域网 IP、绑定地址与防火墙；手机 localhost 是手机自己。

## 正式签名与配置

```powershell
Copy-Item config.example.json config.json
Copy-Item android\key.properties.example android\key.properties
```

config.json 填真实 HTTPS API_BASE_URL 与公开 JPUSH_APPKEY。准备自己的长期 Android keystore，在 key.properties 填路径、别名和密码。文件与密码不提交 Git。

```powershell
flutter build apk --release --dart-define-from-file=config.json
flutter build appbundle --release --dart-define-from-file=config.json
```

没有签名文件或 HTTPS 地址时 release 主动停止。debug 允许开发 HTTP；release 禁止明文流量。iOS 尚未交付。

## 通知接入

包名 `cn.ainews.ai_daily_news`；JPush Flutter 3.5.8，插件依赖 JPush Android SDK 6.2.1。后端填 PUSH_PROVIDER=jpush、JPUSH_APP_KEY、JPUSH_MASTER_SECRET；App 只填匹配 AppKey，不能带 Master Secret。

用户登录后在设置主动同意，再申请 POST_NOTIFICATIONS（Android 13+）；低版本检查系统通知开关。SDK 非必要设备采集、唤醒、地理围栏等开关关闭。没有调用电话/定位权限申请。MainActivity 的 MethodChannel 负责通知权限和系统设置入口。

SDK 登记 Registration ID 到当前会话，前台每两分钟及恢复 App 时刷新。关闭/退出取消待发消息；已受理的消息不能保证撤回。通知只解析有效 report_date，不打开通知给出的任意链接。冷启动与后台点击仍需真机验证。

当前是极光基础通道；华为/小米/OPPO/vivo 等离线通道需另行配置厂商应用、签名、凭据和相应 SDK。强行停止或省电限制可能阻止通知，不承诺全品牌到达。

## 页面与缓存

今日、历史、搜索、收藏、设置五个主页面；详情显示原文摘要、分析、影响、局限、来源与同类新闻。收藏与 Web 同步，长按标签编辑，标签按钮分配标签。密码修改可在 Web 账号页完成。

凭据存系统安全存储；仅最近读取的 7 期公共日报缓存到普通偏好，按服务地址隔离。网络错误/5xx 可读缓存，404 不回退；没有把私人收藏持久存到普通缓存。切换服务器先退出。

## 真机验收

| 场景 | 检查 |
|---|---|
| 登录、重启、退出 | 安全恢复会话，退出清空私有状态 |
| 两账号与 Web/App | 收藏和标签同步，账号之间隔离 |
| 断网 | 已缓存日报标“离线阅读”，未缓存报错 |
| 拒绝通知权限 | 不登记设备，阅读/收藏正常 |
| 开通知并生成非空日报 | 后端 accepted 与手机实际展示分别核对 |
| 重复生成 | 同设备同日期只一条队列记录 |
| 前台、后台、冷启动点击 | 打开对应日期 |
| 退出、关权限、换账号 | 停止旧订阅的后续通知 |
| 杀进程、省电、重启、网络切换 | 记录目标机型到达差异，配置所需厂商通道 |

当前 v0.4.0 尚未重跑 Flutter 自动化测试、构建 APK 或执行上述真机清单。此前版本的结果属于历史记录，不能作为本版通过的证明；详细范围见 [当前测试报告](../docs/AI_CATEGORY_TEST_REPORT.md)。


## v0.4.0 AI 栏目

首页与搜索均增加独立的「AI 人工智能」选项。服务器按中国/国际各四类、每类最多 10 条生成，App 展示返回的全部条目，不截断为 3 条。旧日报缓存按原快照读取，新增栏目在重新构建安装本版 App 后可见。本轮未执行 Flutter 工具链或 APK 构建，新增筛选测试留在 CI 中执行。
