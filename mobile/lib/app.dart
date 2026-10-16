import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'models/news.dart';
import 'state/news_controller.dart';
import 'services/push_service.dart';
import 'screens/news_screens.dart';
import 'screens/search_screen.dart';
import 'screens/bookmarks_screen.dart';
import 'screens/settings_screen.dart';

class NewsApp extends StatefulWidget {
  final NewsController state;
  final PushService push;
  const NewsApp(this.state, this.push, {super.key});
  @override
  State<NewsApp> createState() => _NewsAppState();
}

class _NewsAppState extends State<NewsApp> with WidgetsBindingObserver {
  int index = 0;
  String day = shanghaiDay();
  Timer? timer;
  final navigator = GlobalKey<NavigatorState>();
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    widget.push.openedDay.addListener(openNotification);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      openNotification();
      widget.push.restore();
    });
    timer = Timer.periodic(
      const Duration(minutes: 2),
      (_) => widget.push.sync(),
    );
  }

  @override
  void dispose() {
    timer?.cancel();
    widget.push.openedDay.removeListener(openNotification);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      widget.push.restore();
      widget.state.refreshSaved().catchError((_) {});
    }
  }

  void openNotification() {
    final date = widget.push.openedDay.value;
    if (date != null) {
      navigator.currentState?.popUntil((r) => r.isFirst);
      selectDay(date);
    }
  }

  void selectDay(String value) {
    setState(() {
      day = value;
      index = 0;
    });
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    navigatorKey: navigator,
    debugShowCheckedModeBanner: false,
    title: '智能每日新闻',
    locale: const Locale('zh', 'CN'),
    supportedLocales: const [Locale('zh', 'CN')],
    localizationsDelegates: GlobalMaterialLocalizations.delegates,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xff173e71)),
      scaffoldBackgroundColor: const Color(0xfff5f7fa),
      inputDecorationTheme: const InputDecorationTheme(
        border: OutlineInputBorder(),
        contentPadding: EdgeInsets.all(16),
      ),
    ),
    home: ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) => Scaffold(
        appBar: AppBar(title: const Text('智能每日新闻')),
        body: IndexedStack(
          key: ValueKey(widget.state.api.base),
          index: index,
          children: [
            ReportScreen(
              widget.state,
              day: day,
              selectDay: selectDay,
              openHistory: () => setState(() => index = 1),
            ),
            HistoryScreen(widget.state, selectDay),
            SearchScreen(widget.state),
            BookmarksScreen(widget.state),
            SettingsScreen(widget.state, widget.push),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: index,
          onDestinationSelected: (v) => setState(() => index = v),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.newspaper_outlined),
              label: '今日',
            ),
            NavigationDestination(icon: Icon(Icons.history), label: '历史'),
            NavigationDestination(icon: Icon(Icons.search), label: '搜索'),
            NavigationDestination(
              icon: Icon(Icons.bookmark_border),
              label: '收藏',
            ),
            NavigationDestination(
              icon: Icon(Icons.settings_outlined),
              label: '设置',
            ),
          ],
        ),
      ),
    ),
  );
}
