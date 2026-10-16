typedef Json = Map<String, dynamic>;
String shanghaiDay([DateTime? now]) => (now ?? DateTime.now())
    .toUtc()
    .add(const Duration(hours: 8))
    .toIso8601String()
    .substring(0, 10);
String? reportDate(dynamic value) {
  if (value is! String || !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(value)) {
    return null;
  }
  final date = DateTime.tryParse(value);
  return date != null && date.toIso8601String().startsWith(value)
      ? value
      : null;
}

class News {
  final Json data;
  News(this.data);
  int get id => data['id'] as int;
  String get title => data['title'] ?? data['original_title'] ?? '新闻';
  String get day => data['report_date'] ?? '';
  Json get analysis => Map<String, dynamic>.from(data['analysis'] ?? {});
  String get summary => analysis['summary'] ?? data['original_excerpt'] ?? '';
}

class Report {
  final Json data;
  final bool offline;
  Report(this.data, {this.offline = false});
  List<News> get items => (data['items'] as List? ?? [])
      .map((v) => News(Map<String, dynamic>.from(v)))
      .toList();
}
