import 'dart:async';
import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ai_daily_news/models/news.dart';
import 'package:ai_daily_news/services/api.dart';
import 'package:ai_daily_news/services/push_service.dart';
import 'package:ai_daily_news/services/storage.dart';
import 'package:ai_daily_news/state/news_controller.dart';
import 'support.dart';

void main() {
  test('server URL protects credentials and release transport', () {
    expect(
      normalizeServer('http://localhost:3000/', release: false),
      'http://localhost:3000/api/v1',
    );
    for (final value in [
      'http://example.com',
      'https://user:pass@example.com',
      'https://example.com?q=1',
      'https://example.com/#x',
    ]) {
      expect(
        () => normalizeServer(value, release: true),
        throwsA(isA<ApiError>()),
      );
    }
  });
  test('API decodes Chinese and sends bearer without redirects', () async {
    final api = Api(
      'https://news.test/api/v1',
      client: MockClient((r) async {
        expect(r.headers['Authorization'], 'Bearer test');
        expect(r.followRedirects, false);
        return response({'title': '中国科技'});
      }),
    );
    api.token = 'test';
    expect((await api.call('/search'))['title'], '中国科技');
  });
  test('cache holds seven reports and falls back on network error', () async {
    bool online = true;
    final store = MemoryStorage();
    final state = NewsController(
      Api(
        'https://news.test/api/v1',
        client: MockClient((r) async {
          if (!online) throw http.ClientException('offline');
          return response(report(r.url.pathSegments.last));
        }),
      ),
      store,
    );
    for (int day = 1; day <= 8; day++) {
      await state.report('2026-10-${day.toString().padLeft(2, '0')}');
    }
    expect((jsonDecode(store.get(state.cacheKey)!) as Map).length, 7);
    online = false;
    expect((await state.report('2026-10-08')).offline, true);
    await expectLater(state.report('2026-10-01'), throwsA(isA<ApiError>()));
  });
  test('404 does not use stale cached report', () async {
    var code = 200;
    final state = NewsController(
      Api(
        'https://news.test/api/v1',
        client: MockClient(
          (r) async => response(
            code == 200 ? report('2026-10-13') : {'detail': 'missing'},
            code,
          ),
        ),
      ),
      MemoryStorage(),
    );
    await state.report('2026-10-13');
    code = 404;
    await expectLater(
      state.report('2026-10-13'),
      throwsA(isA<ApiError>().having((e) => e.status, 'status', 404)),
    );
  });
  test('login uses secure session and logout clears private state', () async {
    final store = MemoryStorage();
    final state = NewsController(
      Api(
        'https://news.test/api/v1',
        client: MockClient((r) async {
          if (r.url.path.endsWith('login')) {
            return response({
              'access_token': 'secret',
              'user': {'id': 1, 'username': 'reader', 'display_name': '读者'},
            });
          }
          if (r.url.path.endsWith('/ids')) return response([8]);
          return response({'ok': true});
        }),
      ),
      store,
    );
    await state.login('reader', 'longpassword');
    expect(store.session, contains('secret'));
    expect(store.values.values.any((s) => s.contains('secret')), false);
    expect(state.saved, {8});
    await state.logout();
    expect(store.session, null);
    expect(state.saved, isEmpty);
    expect(state.user, null);
  });
  test('late bookmark response cannot restore logged out user data', () async {
    final done = Completer<http.Response>();
    final state = NewsController(
      Api('https://news.test/api/v1', client: MockClient((_) => done.future)),
      MemoryStorage(),
    );
    state.api.token = 'old';
    state.user = {'id': 1};
    final pending = state.toggle(News({'id': 8, 'report_date': '2026-10-13'}));
    await state.clearSession();
    done.complete(response({'ok': true}));
    await pending;
    expect(state.saved, isEmpty);
  });
  test('old 401 cannot expire a newer session', () async {
    final done = Completer<http.Response>();
    int expired = 0;
    final api = Api(
      'https://news.test/api/v1',
      client: MockClient((_) => done.future),
    );
    api.token = 'old';
    api.onExpired = () => expired++;
    final pending = api.call('/auth/me');
    api.token = 'new';
    done.complete(response({'detail': 'expired'}, 401));
    await expectLater(pending, throwsA(isA<ApiError>()));
    expect(expired, 0);
  });
  test('in flight public report stays in its original server cache', () async {
    final done = Completer<http.Response>();
    final store = MemoryStorage();
    final state = NewsController(
      Api('https://one.test/api/v1', client: MockClient((_) => done.future)),
      store,
    );
    final oldKey = state.cacheKey;
    final pending = state.report('2026-10-13');
    await state.changeServer('https://two.test');
    done.complete(response(report('2026-10-13')));
    await pending;
    expect(store.get(oldKey), isNotNull);
    expect(store.get(state.cacheKey), null);
  });
  test('notification accepts only valid report dates', () {
    expect(
      notificationDate({
        'extras': {'cn.jpush.android.EXTRA': '{"report_date":"2026-10-13"}'},
      }),
      '2026-10-13',
    );
    expect(
      notificationDate({
        'extras': {'report_date': '2026-10-13'},
      }),
      '2026-10-13',
    );
    expect(
      notificationDate({
        'cn.jpush.android.EXTRA': '{"report_date":"2026-10-13"}',
      }),
      '2026-10-13',
    );
    expect(
      notificationDate({
        'extras': {'report_date': '2026-02-30'},
      }),
      null,
    );
    expect(
      notificationDate({
        'extras': {'report_date': 'https://evil.test'},
      }),
      null,
    );
  });
  test('Shanghai date and installation UUID are valid', () {
    expect(shanghaiDay(DateTime.utc(2026, 10, 12, 17)), '2026-10-13');
    expect(
      installationId(),
      matches(
        RegExp(
          r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
        ),
      ),
    );
  });
}
