import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:jpush_flutter/jpush_flutter.dart';
import '../models/news.dart';
import '../state/news_controller.dart';
import 'api.dart';
import 'storage.dart';

String? notificationDate(Map<dynamic, dynamic> event) {
  dynamic value = event;
  // JPush versions wrap Android extras either as a map or as JSON text.
  for (var depth = 0; depth < 4; depth++) {
    if (value is String) {
      try {
        value = jsonDecode(value);
      } catch (_) {
        return null;
      }
    }
    if (value is! Map) return null;
    final date = reportDate(value['report_date']);
    if (date != null) return date;
    value = value['extras'] ?? value['cn.jpush.android.EXTRA'];
  }
  return null;
}

class PushService extends ChangeNotifier {
  final NewsController state;
  final sdk = JPush.newJPush();
  static const permissions = MethodChannel('daily_news/notifications');
  static const appKey = String.fromEnvironment('JPUSH_APPKEY');
  final openedDay = ValueNotifier<String?>(null);
  bool initialized = false, syncing = false, subscribed = false;
  String status = '尚未开启每日提醒';
  PushService(this.state) {
    state.stopPush = stop;
  }
  bool get consent => state.storage.get('push_consent') == 'yes';
  String get deviceKey => 'device:${state.api.base}:${state.user?['id']}';
  Future<bool> allowed() async =>
      await permissions.invokeMethod<bool>('enabled') ?? false;
  Future<void> settings() => permissions.invokeMethod('settings');
  Future<void> start({bool requestPermission = true}) async {
    if (!Platform.isAndroid) throw ApiError(0, '当前仅支持 Android 推送');
    if (state.user == null) throw ApiError(401, '请先登录');
    final config = await state.api.call('/mobile/config');
    if (appKey.isEmpty ||
        config['push_enabled'] != true ||
        config['app_key'] != appKey) {
      throw ApiError(0, '客户端与服务器需要配置同一极光 AppKey');
    }
    final granted = requestPermission
        ? (await permissions.invokeMethod<bool>('request') ?? false)
        : await allowed();
    if (!granted) {
      await unsubscribe();
      status = '系统通知权限已关闭，请在系统设置开启';
      notifyListeners();
      return;
    }
    await state.storage.set('push_consent', 'yes');
    if (!initialized) {
      sdk.setUserRequestNotificationPermission(enable: true);
      sdk.setCollectControl(
        imsi: false,
        mac: false,
        wifi: false,
        bssid: false,
        ssid: false,
        imei: false,
        cell: false,
        gps: false,
      );
      sdk.setWakeEnable(enable: false);
      sdk.enableAutoWakeup(enable: false);
      sdk.setLinkMergeEnable(enable: false);
      sdk.setGeofenceEnable(enable: false);
      sdk.setSmartPushEnable(enable: false);
      sdk.setDataInsightsEnable(enable: false);
      sdk.addEventHandler(
        onOpenNotification: (event) async {
          final date = notificationDate(event);
          if (date != null) {
            openedDay.value = null;
            openedDay.value = date;
          }
        },
        onReceiveNotification: (_) async {},
        onReceiveMessage: (_) async {},
        onReceiveNotificationAuthorization: (_) async {},
        onConnected: (_) async {
          await sync();
        },
      );
      sdk.setup(
        appKey: appKey,
        channel: 'daily-news',
        production: kReleaseMode,
        debug: false,
      );
      initialized = true;
    }
    await sdk.resumePush();
    await sync();
  }

  Future<void> restore() async {
    if (consent && state.user != null) {
      try {
        await start(requestPermission: false);
      } catch (e) {
        status = '$e';
        notifyListeners();
      }
    }
  }

  Future<void> sync() async {
    if (syncing || !initialized || !consent || state.user == null) return;
    syncing = true;
    try {
      if (!await allowed()) {
        await unsubscribe();
        status = '通知权限已关闭';
        return;
      }
      final token = state.api.token, server = state.api.base, key = deviceKey;
      final registration = await sdk.getRegistrationID().timeout(
        const Duration(seconds: 12),
      );
      if (registration.isEmpty) {
        status = '正在连接推送服务，回到 App 后自动重试';
        return;
      }
      if (token != state.api.token || server != state.api.base || !consent) {
        return;
      }
      var installation = state.storage.get('installation_id');
      installation ??= installationId();
      await state.storage.set('installation_id', installation);
      final result = await state.api.call(
        '/devices',
        method: 'POST',
        body: {
          'installation_id': installation,
          'registration_id': registration,
        },
      );
      if (token == state.api.token && server == state.api.base && consent) {
        await state.storage.set(key, result['id']);
        subscribed = true;
        status = '已订阅 · 日报生成后提醒';
      }
    } catch (e) {
      status = '$e';
    } finally {
      syncing = false;
      notifyListeners();
    }
  }

  Future<void> unsubscribe() async {
    final id = state.storage.get(deviceKey);
    if (id != null && state.user != null) {
      await state.api.call('/devices/$id', method: 'DELETE');
      await state.storage.remove(deviceKey);
    }
    subscribed = false;
  }

  Future<void> disable() async {
    await unsubscribe();
    await stop();
  }

  Future<void> stop() async {
    await state.storage.remove('push_consent');
    subscribed = false;
    if (initialized) {
      await sdk.stopPush();
      await sdk.clearAllNotifications();
    }
    status = '已关闭每日提醒';
    notifyListeners();
  }
}
