import 'package:flutter/material.dart';
import '../state/news_controller.dart';
import '../widgets/news_widgets.dart';

class AuthScreen extends StatefulWidget {
  final NewsController state;
  const AuthScreen(this.state, {super.key});
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final form = GlobalKey<FormState>();
  final username = TextEditingController(),
      password = TextEditingController(),
      name = TextEditingController();
  bool register = false, busy = false;
  @override
  void dispose() {
    username.dispose();
    password.dispose();
    name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(register ? '创建账号' : '登录')),
    body: Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Form(
            key: form,
            child: Column(
              children: [
                TextFormField(
                  controller: username,
                  decoration: const InputDecoration(labelText: '用户名'),
                  autofillHints: const [AutofillHints.username],
                  validator: (v) =>
                      RegExp(r'^[A-Za-z0-9_]{3,32}$').hasMatch(v ?? '')
                      ? null
                      : '请输入 3–32 位字母、数字或下划线',
                ),
                if (register)
                  TextFormField(
                    controller: name,
                    maxLength: 60,
                    decoration: const InputDecoration(labelText: '昵称'),
                    validator: (v) => (v ?? '').trim().isEmpty ? '请输入昵称' : null,
                  ),
                TextFormField(
                  controller: password,
                  obscureText: true,
                  enableSuggestions: false,
                  autocorrect: false,
                  decoration: const InputDecoration(labelText: '密码'),
                  validator: (v) =>
                      (v ?? '').length >= 10 && (v ?? '').length <= 128
                      ? null
                      : '密码长度为 10–128 位',
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: busy
                      ? null
                      : () async {
                          if (!form.currentState!.validate()) return;
                          setState(() => busy = true);
                          try {
                            await widget.state.login(
                              username.text,
                              password.text,
                              displayName: register ? name.text.trim() : null,
                            );
                            password.clear();
                            if (context.mounted) Navigator.pop(context);
                          } catch (e) {
                            if (context.mounted) showError(context, e);
                          } finally {
                            if (mounted) setState(() => busy = false);
                          }
                        },
                  child: Text(
                    busy
                        ? '处理中…'
                        : register
                        ? '注册并登录'
                        : '登录',
                  ),
                ),
                TextButton(
                  onPressed: busy
                      ? null
                      : () => setState(() => register = !register),
                  child: Text(register ? '已有账号？登录' : '创建新账号'),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}
