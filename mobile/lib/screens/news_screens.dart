import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../models/news.dart';
import '../state/news_controller.dart';
import '../widgets/news_widgets.dart';

const categories = {
  'politics': '时事政治',
  'finance': '金融经济',
  'technology': '科技发展',
  'ai': 'AI 人工智能',
};

class ReportScreen extends StatefulWidget {
  final NewsController state;
  final String day;
  final ValueChanged<String> selectDay;
  final VoidCallback openHistory;
  const ReportScreen(
    this.state, {
    required this.day,
    required this.selectDay,
    required this.openHistory,
    super.key,
  });
  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  late Future<Report> future;
  String category = '';
  @override
  void initState() {
    super.initState();
    load();
  }

  @override
  void didUpdateWidget(covariant ReportScreen old) {
    super.didUpdateWidget(old);
    if (old.day != widget.day || old.state.api.base != widget.state.api.base) {
      load();
    }
  }

  void load() {
    future = widget.state.report(widget.day);
  }

  @override
  Widget build(BuildContext context) => Column(
    children: [
      Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          children: [
            TextButton.icon(
              icon: const Icon(Icons.calendar_month),
              label: Text(widget.day),
              onPressed: () async {
                final date = await showDatePicker(
                  context: context,
                  initialDate: DateTime.parse(widget.day),
                  firstDate: DateTime(2020),
                  lastDate: DateTime.parse(shanghaiDay()),
                );
                if (date != null) {
                  widget.selectDay(date.toIso8601String().substring(0, 10));
                }
              },
            ),
            const Spacer(),
            TextButton(
              onPressed: widget.openHistory,
              child: const Text('历史日报'),
            ),
          ],
        ),
      ),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (final e in {'': '全部', ...categories}.entries)
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: ChoiceChip(
                  label: Text(e.value),
                  selected: category == e.key,
                  onSelected: (_) => setState(() => category = e.key),
                ),
              ),
          ],
        ),
      ),
      Expanded(
        child: FutureBuilder<Report>(
          future: future,
          builder: (context, s) {
            if (s.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (s.hasError) return ErrorPanel(s.error!, () => setState(load));
            final report = s.data!;
            return RefreshIndicator(
              onRefresh: () async {
                setState(load);
                await future;
              },
              child: ListView(
                padding: const EdgeInsets.all(12),
                physics: const AlwaysScrollableScrollPhysics(),
                children: [
                  if (report.offline)
                    const Card(
                      child: Padding(
                        padding: EdgeInsets.all(12),
                        child: Text('离线阅读 · 已缓存的公共日报'),
                      ),
                    ),
                  if (report.data['status'] == 'partial')
                    const Padding(
                      padding: EdgeInsets.all(8),
                      child: Text('本期部分来源或栏目缺失，详情请查看 Web 数据源页'),
                    ),
                  if (report.items.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Text('本期暂无收录新闻'),
                    ),
                  for (final region in {
                    'china': '中国新闻',
                    'international': '国际新闻',
                  }.entries) ...[
                    Text(
                      region.value,
                      style: Theme.of(context).textTheme.headlineSmall,
                    ),
                    for (final cat in categories.entries)
                      if (category.isEmpty || category == cat.key) ...[
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Text(
                            cat.value,
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                        if (!report.items.any(
                          (n) =>
                              n.analysis['region'] == region.key &&
                              n.analysis['category'] == cat.key,
                        ))
                          const Text('暂无收录'),
                        for (final n in report.items.where(
                          (n) =>
                              n.analysis['region'] == region.key &&
                              n.analysis['category'] == cat.key,
                        ))
                          NewsTile(
                            n,
                            widget.state,
                            open: () => openDetail(context, widget.state, n),
                          ),
                      ],
                    const SizedBox(height: 24),
                  ],
                ],
              ),
            );
          },
        ),
      ),
    ],
  );
}

void openDetail(BuildContext context, NewsController state, News news) {
  Navigator.push(
    context,
    MaterialPageRoute(builder: (_) => DetailScreen(state, news)),
  );
}

class DetailScreen extends StatelessWidget {
  final NewsController state;
  final News news;
  const DetailScreen(this.state, this.news, {super.key});
  @override
  Widget build(BuildContext context) {
    final analysis = news.analysis;
    return Scaffold(
      appBar: AppBar(
        title: const Text('新闻详情'),
        actions: [SaveButton(state, news)],
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(news.title, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 12),
          Text('${news.data['source_name']} · ${news.data['published_at']}'),
          const SizedBox(height: 20),
          Text('原文摘要', style: Theme.of(context).textTheme.titleLarge),
          Text(news.data['original_excerpt'] ?? ''),
          const Divider(height: 36),
          Text(
            news.data['analysis_status'] == 'ai' ? 'AI 分析' : '来源摘要 · 非 AI 分析',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          Text(news.summary),
          for (final entry in {
            'importance_reason': '重要程度说明',
            'why_important': '为什么重要',
            'people_impact': '对普通人的影响',
            'market_impact': '市场影响',
            'short_term': '短期情景',
            'long_term': '长期情景',
          }.entries)
            if ((analysis[entry.key] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 20),
              Text(entry.value, style: Theme.of(context).textTheme.titleMedium),
              Text('${analysis[entry.key]}'),
            ],
          for (final entry in {
            'facts': '已知事实',
            'limitations': '分析局限',
            'industries': '相关行业',
          }.entries)
            if ((analysis[entry.key] as List? ?? []).isNotEmpty) ...[
              const SizedBox(height: 20),
              Text(entry.value, style: Theme.of(context).textTheme.titleMedium),
              for (final value in analysis[entry.key]) Text('• $value'),
            ],
          const SizedBox(height: 24),
          OutlinedButton.icon(
            icon: const Icon(Icons.open_in_new),
            label: const Text('查看新闻原文'),
            onPressed: () async {
              final uri = Uri.tryParse(news.data['url'] ?? '');
              if (uri == null || !['https', 'http'].contains(uri.scheme)) {
                return;
              }
              try {
                if (!await launchUrl(
                      uri,
                      mode: LaunchMode.externalApplication,
                    ) &&
                    context.mounted) {
                  showError(context, '无法打开原文');
                }
              } catch (e) {
                if (context.mounted) showError(context, e);
              }
            },
          ),
          FutureBuilder<dynamic>(
            future: state.api.call(
              '/news/${news.id}',
              query: {'report_date': news.day},
            ),
            builder: (context, s) {
              if (!s.hasData) return const SizedBox.shrink();
              final related = (s.data['related'] as List? ?? []);
              if (related.isEmpty) return const SizedBox.shrink();
              return Column(
                children: [
                  const SizedBox(height: 24),
                  const Text('同类新闻'),
                  for (final item in related)
                    ListTile(
                      title: Text(item['title'] ?? ''),
                      onTap: () => openDetail(
                        context,
                        state,
                        News(Map<String, dynamic>.from(item)),
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class HistoryScreen extends StatefulWidget {
  final NewsController state;
  final ValueChanged<String> selectDay;
  const HistoryScreen(this.state, this.selectDay, {super.key});
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<dynamic> rows = [];
  String? error;
  bool busy = false, more = true;
  @override
  void initState() {
    super.initState();
    load(true);
  }

  Future<void> load(bool reset) async {
    setState(() => busy = true);
    try {
      final next = await widget.state.history(
        before: reset || rows.isEmpty ? null : rows.last['date'],
      );
      if (mounted) {
        setState(() {
          rows = reset ? next : [...rows, ...next];
          more = next.length == 30;
          error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => RefreshIndicator(
    onRefresh: () => load(true),
    child: ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        Text('历史日报', style: Theme.of(context).textTheme.headlineSmall),
        if (error != null) ErrorPanel(error!, () => load(true)),
        for (final row in rows)
          ListTile(
            leading: const Icon(Icons.newspaper),
            title: Text(row['date']),
            subtitle: Text(
              '${row['total']} 条 · ${row['status'] == 'offline' ? '离线缓存' : row['status']}',
            ),
            onTap: () => widget.selectDay(row['date']),
          ),
        if (!busy && rows.isEmpty && error == null)
          const Padding(padding: EdgeInsets.all(24), child: Text('还没有历史日报')),
        if (busy) const Center(child: CircularProgressIndicator()),
        if (!busy && more)
          TextButton(onPressed: () => load(false), child: const Text('加载更多')),
      ],
    ),
  );
}
