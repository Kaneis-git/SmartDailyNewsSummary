import 'package:flutter/material.dart';
import '../models/news.dart';
import '../state/news_controller.dart';
import '../widgets/news_widgets.dart';
import 'auth_screen.dart';
import 'news_screens.dart';

class BookmarksScreen extends StatefulWidget {
  final NewsController state;
  const BookmarksScreen(this.state, {super.key});
  @override
  State<BookmarksScreen> createState() => _BookmarksScreenState();
}

class _BookmarksScreenState extends State<BookmarksScreen> {
  final query = TextEditingController();
  Json? result;
  List<Json> tags = [];
  int page = 1, generation = 0;
  int? tag;
  String? error, identity;
  bool busy = false;
  @override
  void initState() {
    super.initState();
    widget.state.addListener(changed);
    changed();
  }

  void changed() {
    final current =
        '${widget.state.user?['id']}:${widget.state.api.token}:${widget.state.saved.join(',')}';
    if (current != identity) {
      identity = current;
      generation++;
      if (widget.state.user == null) {
        setState(() {
          result = null;
          tags = [];
          tag = null;
          page = 1;
          query.clear();
        });
      } else {
        load();
      }
    }
  }

  @override
  void dispose() {
    widget.state.removeListener(changed);
    query.dispose();
    super.dispose();
  }

  Future<void> load([int next = 1]) async {
    if (widget.state.user == null) return;
    final id = ++generation;
    setState(() => busy = true);
    try {
      final values = await Future.wait([
        widget.state.api.call(
          '/bookmarks',
          query: {
            'q': query.text,
            'page': '$next',
            if (tag != null) 'tag_id': '$tag',
          },
        ),
        widget.state.api.call('/tags'),
      ]);
      if (mounted && id == generation) {
        setState(() {
          result = Map<String, dynamic>.from(values[0]);
          tags = (values[1] as List)
              .map((v) => Map<String, dynamic>.from(v))
              .toList();
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

  Future<void> editTag([Json? existing]) async {
    final input = TextEditingController(text: existing?['name']);
    final value = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(existing == null ? '创建标签' : '重命名标签'),
        content: TextField(controller: input, maxLength: 24, autofocus: true),
        actions: [
          if (existing != null)
            TextButton(
              onPressed: () => Navigator.pop(c, '__DELETE__'),
              child: const Text('删除标签'),
            ),
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, input.text.trim()),
            child: const Text('保存'),
          ),
        ],
      ),
    );
    input.dispose();
    if (value == null || value.isEmpty) return;
    try {
      await widget.state.api.call(
        existing == null ? '/tags' : '/tags/${existing['id']}',
        method: value == '__DELETE__'
            ? 'DELETE'
            : existing == null
            ? 'POST'
            : 'PATCH',
        body: value == '__DELETE__' ? null : {'name': value},
      );
      if (value == '__DELETE__' && tag == existing?['id']) tag = null;
      await load();
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  Future<void> assign(Json row) async {
    final ids = Set<int>.from((row['tags'] as List).map((v) => v['id']));
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(
        builder: (c, change) => AlertDialog(
          title: const Text('设置私人标签'),
          content: SizedBox(
            width: 320,
            child: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (tags.isEmpty) const Text('请先创建标签'),
                  for (final t in tags)
                    CheckboxListTile(
                      title: Text(t['name']),
                      value: ids.contains(t['id']),
                      onChanged: (v) => change(() {
                        if (v == true) {
                          ids.add(t['id']);
                        } else {
                          ids.remove(t['id']);
                        }
                      }),
                    ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(c),
              child: const Text('取消'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(c, true),
              child: const Text('保存'),
            ),
          ],
        ),
      ),
    );
    if (ok != true) return;
    try {
      await widget.state.api.call(
        '/bookmarks/${row['news']['id']}',
        method: 'PUT',
        body: {'tag_ids': ids.toList()},
      );
      await load(page);
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.state.user == null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('登录后查看私人收藏'),
            FilledButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => AuthScreen(widget.state)),
              ),
              child: const Text('登录'),
            ),
          ],
        ),
      );
    }
    return RefreshIndicator(
      onRefresh: () => load(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        physics: const AlwaysScrollableScrollPhysics(),
        children: [
          Text('我的收藏', style: Theme.of(context).textTheme.headlineSmall),
          TextField(
            controller: query,
            decoration: const InputDecoration(labelText: '搜索收藏'),
            onSubmitted: (_) => load(),
          ),
          Wrap(
            spacing: 8,
            children: [
              ChoiceChip(
                label: const Text('全部标签'),
                selected: tag == null,
                onSelected: (_) {
                  tag = null;
                  load();
                },
              ),
              for (final t in tags)
                GestureDetector(
                  onLongPress: () => editTag(t),
                  child: ChoiceChip(
                    label: Text(t['name']),
                    selected: tag == t['id'],
                    onSelected: (_) {
                      tag = t['id'];
                      load();
                    },
                  ),
                ),
              ActionChip(label: const Text('新增标签'), onPressed: () => editTag()),
            ],
          ),
          const Text('长按标签可重命名或删除，新闻会保留。'),
          if (busy) const LinearProgressIndicator(),
          if (error != null) ErrorPanel(error!, () => load(page)),
          if (!busy && result != null) ...[
            Text('共 ${result!['total']} 条收藏'),
            if (result!['total'] == 0)
              const Padding(
                padding: EdgeInsets.all(24),
                child: Text('这里还没有收藏'),
              ),
            for (final row in result!['items'])
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  NewsTile(
                    News(Map<String, dynamic>.from(row['news'])),
                    widget.state,
                    open: () => openDetail(
                      context,
                      widget.state,
                      News(Map<String, dynamic>.from(row['news'])),
                    ),
                  ),
                  TextButton(
                    onPressed: () => assign(Map<String, dynamic>.from(row)),
                    child: Text(
                      (row['tags'] as List).isEmpty
                          ? '设置标签'
                          : (row['tags'] as List)
                                .map((t) => t['name'])
                                .join(' · '),
                    ),
                  ),
                ],
              ),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                TextButton(
                  onPressed: page > 1 ? () => load(page - 1) : null,
                  child: const Text('上一页'),
                ),
                Text('第 $page 页'),
                TextButton(
                  onPressed: page * 20 < (result!['total'] as int)
                      ? () => load(page + 1)
                      : null,
                  child: const Text('下一页'),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
