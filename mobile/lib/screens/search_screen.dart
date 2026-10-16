import 'package:flutter/material.dart';
import '../models/news.dart';
import '../state/news_controller.dart';
import '../widgets/news_widgets.dart';
import 'news_screens.dart';

class SearchScreen extends StatefulWidget {
  final NewsController state;
  const SearchScreen(this.state, {super.key});
  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final query = TextEditingController();
  String region = '', category = '';
  DateTimeRange? dates;
  int page = 1, generation = 0;
  Json? result;
  String? error;
  bool busy = false;
  @override
  void dispose() {
    query.dispose();
    super.dispose();
  }

  Future<void> search([int next = 1]) async {
    final id = ++generation;
    setState(() => busy = true);
    try {
      final Json data = await widget.state.api.call(
        '/search',
        query: {
          'q': query.text,
          'page': '$next',
          if (region.isNotEmpty) 'region': region,
          if (category.isNotEmpty) 'category': category,
          if (dates != null)
            'date_from': dates!.start.toIso8601String().substring(0, 10),
          if (dates != null)
            'date_to': dates!.end.toIso8601String().substring(0, 10),
        },
      );
      if (mounted && id == generation) {
        setState(() {
          result = data;
          page = next;
          error = null;
        });
      }
    } catch (e) {
      if (mounted && id == generation) setState(() => error = '$e');
    } finally {
      if (mounted && id == generation) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(16),
    children: [
      Text('搜索新闻', style: Theme.of(context).textTheme.headlineSmall),
      TextField(
        controller: query,
        maxLength: 100,
        decoration: const InputDecoration(
          labelText: '搜索关键词',
          hintText: '人工智能、经济政策…',
        ),
        onSubmitted: (_) => search(),
      ),
      Wrap(
        spacing: 12,
        children: [
          DropdownButton<String>(
            value: region,
            items: [
              for (final e in {
                '': '全部地区',
                'china': '中国新闻',
                'international': '国际新闻',
              }.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value)),
            ],
            onChanged: (v) => setState(() => region = v!),
          ),
          DropdownButton<String>(
            value: category,
            items: [
              for (final e in {'': '全部领域', ...categories}.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value)),
            ],
            onChanged: (v) => setState(() => category = v!),
          ),
          TextButton(
            onPressed: () async {
              final picked = await showDateRangePicker(
                context: context,
                firstDate: DateTime(2020),
                lastDate: DateTime.parse(shanghaiDay()),
                initialDateRange: dates,
              );
              if (picked != null) setState(() => dates = picked);
            },
            child: Text(
              dates == null
                  ? '日期范围'
                  : '${dates!.start.toIso8601String().substring(0, 10)} 至 ${dates!.end.toIso8601String().substring(0, 10)}',
            ),
          ),
          if (dates != null)
            IconButton(
              tooltip: '清除日期',
              onPressed: () => setState(() => dates = null),
              icon: const Icon(Icons.close),
            ),
        ],
      ),
      FilledButton(
        onPressed: busy ? null : () => search(),
        child: const Text('搜索'),
      ),
      if (busy) const LinearProgressIndicator(),
      if (error != null) ErrorPanel(error!, () => search(page)),
      if (!busy && result != null) ...[
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 16),
          child: Text('找到 ${result!['total']} 条新闻'),
        ),
        if (result!['total'] == 0) const Text('暂无匹配新闻'),
        for (final value in result!['items'])
          NewsTile(
            News(Map<String, dynamic>.from(value)),
            widget.state,
            open: () => openDetail(
              context,
              widget.state,
              News(Map<String, dynamic>.from(value)),
            ),
          ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            TextButton(
              onPressed: page > 1 ? () => search(page - 1) : null,
              child: const Text('上一页'),
            ),
            Text('第 $page 页'),
            TextButton(
              onPressed: page * 20 < (result!['total'] as int)
                  ? () => search(page + 1)
                  : null,
              child: const Text('下一页'),
            ),
          ],
        ),
      ],
    ],
  );
}
