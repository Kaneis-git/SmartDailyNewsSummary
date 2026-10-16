import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/news.dart';

class ApiError implements Exception {
  final int status;
  final String message;
  ApiError(this.status, this.message);
  @override
  String toString() => message;
}

String normalizeServer(String input, {required bool release}) {
  final u = Uri.tryParse(input.trim());
  if (u == null ||
      u.host.isEmpty ||
      !['http', 'https'].contains(u.scheme) ||
      (release && u.scheme != 'https') ||
      u.userInfo.isNotEmpty ||
      u.hasQuery ||
      u.hasFragment) {
    throw ApiError(0, '请输入有效的服务地址，正式版必须使用 HTTPS');
  }
  var path = u.path.replaceAll(RegExp(r'/+$'), '');
  if (!path.endsWith('/api/v1')) path += '/api/v1';
  return u.replace(path: path).toString();
}

class Api {
  String base;
  String? token;
  final http.Client client;
  void Function()? onExpired;
  Api(this.base, {http.Client? client}) : client = client ?? http.Client();
  Future<dynamic> call(
    String path, {
    String method = 'GET',
    Json? body,
    Map<String, String>? query,
  }) async {
    final startToken = token, startBase = base;
    final uri = Uri.parse(
      '$base$path',
    ).replace(queryParameters: query?.isEmpty == true ? null : query);
    final request = http.Request(method, uri)..followRedirects = false;
    request.headers['Accept'] = 'application/json';
    if (token != null) request.headers['Authorization'] = 'Bearer $token';
    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }
    try {
      final response = await http.Response.fromStream(
        await client.send(request).timeout(const Duration(seconds: 15)),
      ).timeout(const Duration(seconds: 15));
      dynamic data;
      try {
        data = jsonDecode(utf8.decode(response.bodyBytes));
      } catch (_) {
        data = null;
      }
      if (response.statusCode == 401 &&
          startToken != null &&
          token == startToken &&
          base == startBase) {
        onExpired?.call();
      }
      if (response.statusCode < 200 || response.statusCode >= 300) {
        final detail = data is Map ? data['detail'] : null;
        throw ApiError(
          response.statusCode,
          detail is String ? detail : '请求失败（${response.statusCode}）',
        );
      }
      return data;
    } on ApiError {
      rethrow;
    } catch (_) {
      throw ApiError(0, '连接失败，请检查网络与服务地址');
    }
  }
}
