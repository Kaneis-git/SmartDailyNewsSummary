import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:ai_daily_news/services/api.dart';
import 'package:ai_daily_news/state/news_controller.dart';
import 'package:ai_daily_news/screens/auth_screen.dart';
import 'package:ai_daily_news/screens/bookmarks_screen.dart';
import 'package:ai_daily_news/screens/news_screens.dart';
import 'package:ai_daily_news/screens/search_screen.dart';
import 'support.dart';

NewsController stateWith(MockClient client, [MemoryStorage? store]) =>
    NewsController(
      Api('https://news.test/api/v1', client: client),
      store ?? MemoryStorage(),
    );
void main() {
  testWidgets(
    'visitor collection asks login without reading private endpoint',
    (t) async {
      int calls = 0;
      final state = stateWith(
        MockClient((_) async {
          calls++;
          return response({});
        }),
      );
      await t.pumpWidget(
        MaterialApp(home: Scaffold(body: BookmarksScreen(state))),
      );
      expect(find.text('登录后查看私人收藏'), findsOneWidget);
      expect(calls, 0);
    },
  );
  testWidgets('login validates fields before network', (t) async {
    int calls = 0;
    final state = stateWith(
      MockClient((_) async {
        calls++;
        return response({});
      }),
    );
    await t.pumpWidget(MaterialApp(home: AuthScreen(state)));
    await t.tap(find.widgetWithText(FilledButton, '登录'));
    await t.pumpAndSettle();
    expect(find.text('密码长度为 10–128 位'), findsOneWidget);
    expect(calls, 0);
  });
  testWidgets('missing report shows retry and history', (t) async {
    final state = stateWith(
      MockClient((_) async => response({'detail': '日报未生成'}, 404)),
    );
    await t.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ReportScreen(
            state,
            day: '2026-10-13',
            selectDay: (_) {},
            openHistory: () {},
          ),
        ),
      ),
    );
    await t.pumpAndSettle();
    expect(find.text('日报未生成'), findsOneWidget);
    expect(find.text('历史日报'), findsOneWidget);
    expect(find.text('重试'), findsOneWidget);
  });
  testWidgets('offline report states cached origin', (t) async {
    final store = MemoryStorage();
    final state = stateWith(
      MockClient((_) async => throw http.ClientException('offline')),
      store,
    );
    await store.set(
      state.cacheKey,
      jsonEncode({'2026-10-13': report('2026-10-13')}),
    );
    await t.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ReportScreen(
            state,
            day: '2026-10-13',
            selectDay: (_) {},
            openHistory: () {},
          ),
        ),
      ),
    );
    await t.pumpAndSettle();
    expect(find.text('离线阅读 · 已缓存的公共日报'), findsOneWidget);
  });
  testWidgets('Chinese search sends query and displays empty result', (
    t,
  ) async {
    String? query;
    final state = stateWith(
      MockClient((r) async {
        query = r.url.queryParameters['q'];
        return response({'items': [], 'total': 0, 'page': 1, 'page_size': 20});
      }),
    );
    await t.pumpWidget(MaterialApp(home: Scaffold(body: SearchScreen(state))));
    await t.enterText(find.byType(TextField), '人工智能');
    await t.tap(find.widgetWithText(FilledButton, '搜索'));
    await t.pumpAndSettle();
    expect(query, '人工智能');
    expect(find.text('暂无匹配新闻'), findsOneWidget);
  });
  testWidgets('AI category search sends the independent AI filter', (t) async {
    String? category;
    final state = stateWith(
      MockClient((r) async {
        category = r.url.queryParameters['category'];
        return response({'items': [], 'total': 0, 'page': 1, 'page_size': 20});
      }),
    );
    await t.pumpWidget(MaterialApp(home: Scaffold(body: SearchScreen(state))));
    await t.tap(find.text('全部领域'));
    await t.pumpAndSettle();
    await t.tap(find.text('AI 人工智能').last);
    await t.pumpAndSettle();
    await t.tap(find.widgetWithText(FilledButton, '搜索'));
    await t.pumpAndSettle();
    expect(category, 'ai');
    expect(find.text('暂无匹配新闻'), findsOneWidget);
  });
}
