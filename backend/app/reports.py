import re
from urllib.parse import quote
from sqlalchemy import select
from .clock import iso
from .models import ReportItem
from ai_service.taxonomy import CATEGORY_NAMES

REGION_NAMES = {"china": "中国新闻", "international": "国际新闻"}


def report_dict(session, report, include_items=True):
    result = {"date": report.report_date.isoformat(), "window_start": iso(report.window_start),
              "window_end": iso(report.window_end), "generated_at": iso(report.generated_at),
              "status": report.status, "coverage": report.coverage, "source_results": report.source_results,
              "total": sum(report.coverage.values())}
    if include_items:
        result["items"] = [row.snapshot for row in session.scalars(select(ReportItem).where(
            ReportItem.report_id == report.id).order_by(ReportItem.position))]
    return result


def md_text(text):
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", str(text)).replace("\n", " ")


def as_markdown(report):
    lines = [f"# {report['date']} 全球新闻日报", "", f"统计窗口（UTC）：{report['window_start']} 至 {report['window_end']}",
             f"生成时间（UTC）：{report['generated_at']}", "", "事实以原始来源为准。AI 影响分析为条件性推断。", ""]
    for region, region_name in REGION_NAMES.items():
        lines.append(f"## {region_name}")
        for category, category_name in CATEGORY_NAMES.items():
            lines.extend(["", f"### {category_name}", ""])
            rows = [item for item in report["items"] if item["analysis"]["region"] == region and item["analysis"]["category"] == category]
            if not rows:
                lines.extend(["本期暂无收录。", ""])
            for item in rows:
                analysis = item["analysis"]
                lines.extend([f"#### {md_text(item['title'])}", "",
                    f"来源：[{md_text(item['source_name'])}](<{quote(item['url'], safe=':/?=&%#@+~,;') }>)",
                    f"发布时间：{item['published_at']}", f"重要程度：{'★' * analysis['importance']}（编辑排序）",
                    f"分析模式：{item['analysis_status']}", "", f"摘要：{md_text(analysis['summary'])}", ""])
                for key, name in [("why_important", "为什么重要"), ("people_impact", "普通人影响"), ("market_impact", "市场影响"), ("short_term", "短期情景"), ("long_term", "长期情景")]:
                    if analysis[key]:
                        lines.extend([f"{name}：{md_text(analysis[key])}", ""])
                lines.extend(["局限：" + "；".join(md_text(x) for x in analysis["limitations"]), ""])
    errors = [r for r in report["source_results"] if r["status"] == "error"]
    if errors:
        lines.extend(["## 本期来源异常", ""] + [f"- {md_text(r['name'])}：{md_text(r['message'])}" for r in errors])
    return "\n".join(lines)
