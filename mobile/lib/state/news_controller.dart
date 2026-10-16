import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../services/api.dart';
import '../services/storage.dart';
import '../models/news.dart';

class NewsController extends ChangeNotifier {
  final Api api;
  final AppStorage storage;
  Json? user;
  Set<int> saved = {};
  String? startupError;
  Future<void> Function()? stopPush;
  NewsController(this.api, this.storage) {
    api.onExpired = () {
      clearSession();
    };
  }
  Future<void> initialize() async {
    try {
      final stored = await storage.readSession();
      if (stored != null) {
        final session = jsonDecode(stored) as Json;
        if (session['server'] == api.base) {
          api.token = session['token'];
          user = Map<String, dynamic>.from(await api.call('/auth/me'));
          await refreshSaved();
        } else {
          await storage.writeSession(null);
        }
      }
    } catch (e) {
      startupError = '$e';
    }
    notifyListeners();
  }

  Future<void> login(
    String username,
    String password, {
    String? displayName,
  }) async {
    final Json data = await api.call(
      displayName == null ? '/auth/login' : '/auth/register',
      method: 'POST',
      body: {
        'username': username,
        'password': password,
        'platform': 'android',
        'display_name': ?displayName,
      },
    );
    api.token = data['access_token'];
    user = Map<String, dynamic>.from(data['user']);
    await storage.writeSession(
      jsonEncode({'server': api.base, 'token': api.token}),
    );
    notifyListeners();
    try {
      await refreshSaved();
    } catch (e) {
      startupError = '$e';
    }
  }

  Future<void> clearSession() async {
    api.token = null;
    user = null;
    saved = {};
    notifyListeners();
    await storage.writeSession(null);
    try {
      await stopPush?.call();
    } catch (e) {
      startupError = '$e';
    }
  }

  Future<void> logout({bool all = false}) async {
    await api.call(all ? '/auth/logout-all' : '/auth/logout', method: 'POST');
    await clearSession();
  }

  Future<void> changeServer(String value) async {
    if (user != null) throw ApiError(0, '请先退出账号，再更换服务器');
    final next = normalizeServer(value, release: kReleaseMode);
    await clearSession();
    api.base = next;
    await storage.set('server', next);
    notifyListeners();
  }

  Future<void> refreshSaved() async {
    if (api.token == null) return;
    final token = api.token, server = api.base;
    final data = await api.call('/bookmarks/ids');
    if (token == api.token && server == api.base) {
      saved = Set<int>.from(data);
      notifyListeners();
    }
  }

  Future<void> toggle(News news) async {
    if (user == null) throw ApiError(401, '请先登录后收藏');
    final token = api.token,
        server = api.base,
        remove = saved.contains(news.id);
    await api.call(
      '/bookmarks/${news.id}',
      method: remove ? 'DELETE' : 'PUT',
      body: remove ? null : {'report_date': news.day},
    );
    if (token == api.token && server == api.base) {
      if (remove) {
        saved.remove(news.id);
      } else {
        saved.add(news.id);
      }
      notifyListeners();
    }
  }

  String get cacheKey => 'reports:${api.base}';
  Json _cache(String key) {
    try {
      return Map<String, dynamic>.from(jsonDecode(storage.get(key) ?? '{}'));
    } catch (_) {
      return {};
    }
  }

  Future<Report> report(String day) async {
    final key = cacheKey;
    try {
      final Json result = Map<String, dynamic>.from(
        await api.call('/reports/$day'),
      );
      final cache = _cache(key);
      cache.remove(day);
      cache[day] = result;
      while (cache.length > 7) {
        cache.remove(cache.keys.first);
      }
      await storage.set(key, jsonEncode(cache));
      return Report(result);
    } on ApiError catch (e) {
      final cached = _cache(key)[day];
      if (cached != null && (e.status == 0 || e.status >= 500)) {
        return Report(Map<String, dynamic>.from(cached), offline: true);
      }
      rethrow;
    }
  }

  Future<List<dynamic>> history({String? before}) async {
    try {
      return List<dynamic>.from(
        await api.call('/reports', query: {'limit': '30', 'before': ?before}),
      );
    } on ApiError catch (e) {
      if (e.status != 0 && e.status < 500) rethrow;
      final rows =
          _cache(cacheKey).entries
              .where((v) => before == null || v.key.compareTo(before) < 0)
              .toList()
            ..sort((a, b) => b.key.compareTo(a.key));
      if (rows.isEmpty) rethrow;
      return rows
          .map(
            (r) => {
              'date': r.key,
              'total': (r.value['items'] as List).length,
              'status': 'offline',
            },
          )
          .toList();
    }
  }

  Future<void> clearCache() => storage.remove(cacheKey);
}
