import 'package:flutter/material.dart';
import '../models/news.dart';
import '../state/news_controller.dart';

void showError(BuildContext context, Object error) {
  if (context.mounted) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('$error')));
  }
}

class ErrorPanel extends StatelessWidget {
  final Object error;
  final VoidCallback retry;
  const ErrorPanel(this.error, this.retry, {super.key});
  @override
  Widget build(BuildContext context) => Center(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$error', textAlign: TextAlign.center),
          const SizedBox(height: 12),
          FilledButton(onPressed: retry, child: const Text('重试')),
        ],
      ),
    ),
  );
}

class SaveButton extends StatefulWidget {
  final NewsController state;
  final News news;
  final VoidCallback? onChanged;
  const SaveButton(this.state, this.news, {this.onChanged, super.key});
  @override
  State<SaveButton> createState() => _SaveButtonState();
}

class _SaveButtonState extends State<SaveButton> {
  bool busy = false;
  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: widget.state,
    builder: (context, _) => IconButton(
      tooltip: widget.state.saved.contains(widget.news.id) ? '取消收藏' : '收藏',
      onPressed: busy
          ? null
          : () async {
              setState(() => busy = true);
              try {
                await widget.state.toggle(widget.news);
                widget.onChanged?.call();
              } catch (e) {
                if (context.mounted) showError(context, e);
              } finally {
                if (mounted) setState(() => busy = false);
              }
            },
      icon: Icon(
        widget.state.saved.contains(widget.news.id)
            ? Icons.bookmark
            : Icons.bookmark_border,
      ),
    ),
  );
}

class NewsTile extends StatelessWidget {
  final News news;
  final NewsController state;
  final VoidCallback open;
  final VoidCallback? onChanged;
  const NewsTile(
    this.news,
    this.state, {
    required this.open,
    this.onChanged,
    super.key,
  });
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            onTap: open,
            title: Text(
              news.title,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            subtitle: Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                news.summary,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            trailing: SaveButton(state, news, onChanged: onChanged),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Text(
              '${news.data['source_name']} · ${news.day}',
              style: Theme.of(context).textTheme.labelMedium,
            ),
          ),
        ],
      ),
    ),
  );
}
