import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'app.dart';
import 'services/api.dart';
import 'services/storage.dart';
import 'services/push_service.dart';
import 'state/news_controller.dart';

// App 入口：恢复服务地址与会话，再注入新闻状态和推送服务。
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final storage = DeviceStorage(await SharedPreferences.getInstance());
  const configured = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:3000/api/v1',
  );
  final api = Api(
    normalizeServer(storage.get('server') ?? configured, release: kReleaseMode),
  );
  final state = NewsController(api, storage);
  await state.initialize();
  runApp(NewsApp(state, PushService(state)));
}
