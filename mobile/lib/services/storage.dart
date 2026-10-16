import 'dart:math';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

abstract class AppStorage {
  String? get(String key);
  Future<void> set(String key, String value);
  Future<void> remove(String key);
  Future<String?> readSession();
  Future<void> writeSession(String? value);
}

class DeviceStorage implements AppStorage {
  final SharedPreferences preferences;
  final FlutterSecureStorage secure = const FlutterSecureStorage();
  DeviceStorage(this.preferences);
  @override
  String? get(String key) => preferences.getString(key);
  @override
  Future<void> set(String key, String value) async {
    await preferences.setString(key, value);
  }

  @override
  Future<void> remove(String key) async {
    await preferences.remove(key);
  }

  @override
  Future<String?> readSession() => secure.read(key: 'news_session');
  @override
  Future<void> writeSession(String? value) => value == null
      ? secure.delete(key: 'news_session')
      : secure.write(key: 'news_session', value: value);
}

String installationId() {
  final bytes = List<int>.generate(16, (_) => Random.secure().nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final hex = bytes.map((v) => v.toRadixString(16).padLeft(2, '0')).join();
  return '${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}';
}
