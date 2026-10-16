import 'dart:convert';
import 'package:ai_daily_news/services/storage.dart';
import 'package:http/http.dart' as http;

class MemoryStorage implements AppStorage {
  final Map<String, String> values = {};
  String? session;
  @override
  String? get(String key) => values[key];
  @override
  Future<void> set(String key, String value) async {
    values[key] = value;
  }

  @override
  Future<void> remove(String key) async {
    values.remove(key);
  }

  @override
  Future<String?> readSession() async => session;
  @override
  Future<void> writeSession(String? value) async {
    session = value;
  }
}

http.Response response(Object data, [int code = 200]) => http.Response.bytes(
  utf8.encode(jsonEncode(data)),
  code,
  headers: {'content-type': 'application/json; charset=utf-8'},
);
Map<String, dynamic> report(String date) => {
  'date': date,
  'status': 'ready',
  'items': [],
};
