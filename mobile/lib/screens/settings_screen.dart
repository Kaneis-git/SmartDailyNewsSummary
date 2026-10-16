import 'package:flutter/material.dart';
import '../state/news_controller.dart';
import '../services/push_service.dart';
import '../widgets/news_widgets.dart';
import 'auth_screen.dart';

class SettingsScreen extends StatefulWidget {
  final NewsController state;
  final PushService push;
  const SettingsScreen(this.state, this.push, {super.key});
  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool busy = false;
  Future<void> run(Future<void> Function() action) async {
    setState(() => busy = true);
    try {
      await action();
    } catch (e) {
      if (mounted) showError(context, e);
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> changeServer() async {
    final input = TextEditingController(text: widget.state.api.base);
    final value = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('新闻服务地址'),
        content: TextField(controller: input, keyboardType: TextInputType.url),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('取消'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, input.text),
            child: const Text('保存'),
          ),
        ],
      ),
    );
    input.dispose();
    if (value != null) await widget.state.changeServer(value);
  }

  Future<void> enable() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('开启每日新闻提醒'),
        content: const Text(
          '同意后使用极光推送服务，将设备推送标识关联到当前账号，用于在日报生成后通知你。可以随时关闭；不开启也能阅读新闻。',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c, false),
            child: const Text('暂不开启'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(c, true),
            child: const Text('同意并继续'),
          ),
        ],
      ),
    );
    if (ok == true) await widget.push.start();
  }

  Future<void> deliveries() async {
    final values = await widget.state.api.call('/notifications/deliveries');
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (c) => AlertDialog(
        title: const Text('最近通知记录'),
        content: SizedBox(
          width: 350,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if ((values as List).isEmpty) const Text('暂无通知记录'),
                for (final row in values)
                  ListTile(
                    title: Text('${row['report_date']} · ${row['status']}'),
                    subtitle: Text(row['message']),
                  ),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(c),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) => ListenableBuilder(
    listenable: Listenable.merge([widget.state, widget.push]),
    builder: (context, _) => ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text('设置', style: Theme.of(context).textTheme.headlineSmall),
        if (busy) const LinearProgressIndicator(),
        if (widget.state.startupError != null) Text(widget.state.startupError!),
        if (widget.state.user == null)
          ListTile(
            title: const Text('登录或注册'),
            subtitle: const Text('同步收藏与私人标签'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => AuthScreen(widget.state)),
            ),
          )
        else ...[
          ListTile(
            title: Text(widget.state.user!['display_name']),
            subtitle: Text('@${widget.state.user!['username']}'),
          ),
          Wrap(
            children: [
              TextButton(
                onPressed: busy ? null : () => run(() => widget.state.logout()),
                child: const Text('退出当前设备'),
              ),
              TextButton(
                onPressed: busy
                    ? null
                    : () => run(() => widget.state.logout(all: true)),
                child: const Text('退出全部设备'),
              ),
            ],
          ),
        ],
        const Divider(),
        SwitchListTile(
          title: const Text('每日新闻提醒'),
          subtitle: Text(widget.push.status),
          value: widget.push.consent,
          onChanged: busy ? null : (v) => run(v ? enable : widget.push.disable),
        ),
        ListTile(
          title: const Text('系统通知设置'),
          onTap: () => run(widget.push.settings),
        ),
        if (widget.state.user != null)
          ListTile(
            title: const Text('最近通知记录'),
            subtitle: const Text('accepted 表示服务商受理，不代表手机已展示'),
            onTap: () => run(deliveries),
          ),
        const Divider(),
        ListTile(
          title: const Text('新闻服务地址'),
          subtitle: Text(widget.state.api.base),
          onTap: busy ? null : () => run(changeServer),
        ),
        ListTile(
          title: const Text('清除离线缓存'),
          subtitle: const Text('保留账号和服务器收藏'),
          onTap: () => run(() async {
            await widget.state.clearCache();
            if (context.mounted) {
              ScaffoldMessenger.of(
                context,
              ).showSnackBar(const SnackBar(content: Text('已清除缓存')));
            }
          }),
        ),
        const Padding(
          padding: EdgeInsets.all(16),
          child: Text(
            'AI Daily News Assistant 0.4.0\n默认北京时间 08:00 开始生成，完成后提醒。\n事实与预测请结合原文核对。',
          ),
        ),
      ],
    ),
  );
}
