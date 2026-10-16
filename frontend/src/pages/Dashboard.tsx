import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  API,
  ApiError,
  dateTime,
  errorText,
  request,
  todayShanghai,
} from "../api";
import type { Category, Region, Report } from "../types";
import { useApp } from "../state";
import { NewsCard } from "../components/NewsCard";
import {
  categoryNames,
  Empty,
  ErrorBox,
  Icon,
  regionNames,
} from "../components/ui";

export function Dashboard() {
  const { health, job } = useApp();
  const [params, setParams] = useSearchParams();
  const today = health?.today ?? todayShanghai();
  const day = params.get("date") || today;
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [region, setRegion] = useState<Region | "all">("all");
  const [category, setCategory] = useState<Category | "all">("all");
  useEffect(() => {
    let current = true;
    setLoading(true);
    setError("");
    setReport(null);
    request<Report>(`/reports/${day}`)
      .then((data) => {
        if (current) setReport(data);
      })
      .catch((e) => {
        if (current && !(e instanceof ApiError && e.status === 404))
          setError(errorText(e));
      })
      .finally(() => {
        if (current) setLoading(false);
      });
    return () => {
      current = false;
    };
  }, [day, job?.finished_at, retry]);
  const regions = (["china", "international"] as Region[]).filter(
    (value) => region === "all" || value === region,
  );
  const categories = (
    Object.keys(categoryNames) as Category[]
  ).filter((value) => category === "all" || value === category);
  const aiCount =
    report?.items.filter((i) => i.analysis_status === "ai").length ?? 0;
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">YOUR DAILY BRIEFING</div>
          <h1>{day === today ? "今日新闻简报" : "历史新闻简报"}</h1>
          <p>中国与世界，值得了解的每一件事。</p>
        </div>
        <label className="date-picker">
          <span>日报日期</span>
          <input
            type="date"
            value={day}
            max={today}
            onChange={(e) => {
              if (e.target.value) setParams({ date: e.target.value });
            }}
          />
        </label>
      </div>
      <section className="briefing-banner">
        <div>
          <span className="banner-tag">DAILY NEWS · 每日精选</span>
          <h2>把世界的变化，读清楚。</h2>
          <p>聚焦政治、金融、科技与 AI。每个区域各领域精选最多 {health?.max_per_section ?? 10} 条重要新闻。</p>
        </div>
        <div className="banner-date">
          <strong>{day.slice(5).replace("-", " / ")}</strong>
          <span>{day.slice(0, 4)} · 北京时间</span>
        </div>
      </section>
      <div className="stats">
        <div>
          <span>本期新闻</span>
          <strong>
            {report ? report.total : "—"}
            <small>条</small>
          </strong>
        </div>
        <div>
          <span>成功读取来源</span>
          <strong>
            {report
              ? report.source_results.filter((s) => s.status === "ok").length
              : "—"}
            <small>个</small>
          </strong>
        </div>
        <div>
          <span>AI 分析完成</span>
          <strong>
            {report ? aiCount : "—"}
            <small>条</small>
          </strong>
        </div>
        <div>
          <span>每日触发</span>
          <strong>
            {health?.schedule ?? "08:00"}
            <small>北京时间</small>
          </strong>
        </div>
      </div>
      {report && (
        <div className="report-meta">
          <span>
            统计窗口：{dateTime(report.window_start)} —{" "}
            {dateTime(report.window_end)} · 生成于{" "}
            {dateTime(report.generated_at)}
          </span>
          <a className="text-button" href={`${API}/reports/${day}/markdown`}>
            <Icon name="download" size={16} />
            导出日报
          </a>
        </div>
      )}
      {report?.status === "partial" && (
        <div className="notice">
          本期部分收录：部分栏目暂无新闻或来源暂不可用。
          <Link to="/sources">查看来源状态 →</Link>
        </div>
      )}
      {health && !health.ai_enabled && (
        <div className="notice subtle">
          当前为来源摘要模式。配置模型后，可生成中文 AI 总结和影响分析。
        </div>
      )}
      <div className="filter-panel">
        <div className="segment" aria-label="新闻区域">
          {(["all", "china", "international"] as const).map((value) => (
            <button
              key={value}
              aria-pressed={region === value}
              className={region === value ? "selected" : ""}
              onClick={() => setRegion(value)}
            >
              {value === "all" ? "全部新闻" : regionNames[value]}
            </button>
          ))}
        </div>
        <div className="topic-tabs" aria-label="新闻领域">
          {(["all", ...Object.keys(categoryNames)] as (Category | "all")[]).map(
            (value) => (
              <button
                aria-pressed={category === value}
                key={value}
                className={category === value ? "selected" : ""}
                onClick={() => setCategory(value)}
              >
                {value === "all" ? "全部领域" : categoryNames[value]}
              </button>
            ),
          )}
        </div>
      </div>
      {error ? (
        <ErrorBox message={error} retry={() => setRetry((r) => r + 1)} />
      ) : loading ? (
        <div className="loading" role="status">
          正在读取日报…
        </div>
      ) : !report ? (
        <Empty
          title={day === today ? "今天的早报还未生成" : "这一天还没有日报"}
        >
          <p>
            {day === today && health?.report_due
              ? "点击右上角“更新早报”，或等待自动任务完成。"
              : "早报在北京时间每日计划时间触发生成。"}
          </p>
          <Link className="text-button" to="/history">
            查看已有日报 <Icon name="arrow" size={16} />
          </Link>
        </Empty>
      ) : (
        regions.map((r, rIndex) => (
          <section className="region-section" key={r}>
            <div className="section-heading">
              <h2>
                <span className="section-number">0{rIndex + 1}</span>
                {regionNames[r]}
              </h2>
              <span>
                {r === "china" ? "CHINA" : "INTERNATIONAL"} /{" "}
                {report.items.filter((i) => i.analysis.region === r).length} 条
              </span>
            </div>
            {categories.map((c) => {
              const items = report.items.filter(
                (i) => i.analysis.region === r && i.analysis.category === c,
              );
              return (
                <section key={c} className={`category-section ${c}`}>
                  <h3 className="category-heading">
                    <span />
                    {categoryNames[c]}
                    <small className="category-count">{items.length} 条</small>
                  </h3>
                  {items.length ? (
                    <div className="news-grid">
                      {items.map((item, i) => (
                        <NewsCard
                          key={item.id}
                          item={item}
                          featured={i === 0 && item.analysis.importance >= 4}
                        />
                      ))}
                    </div>
                  ) : (
                    <div className="section-empty">
                      {c === "ai" && !Object.hasOwn(report.coverage, `${r}.ai`)
                        ? "此历史日报生成时尚未开设 AI 栏目"
                        : "本期暂无收录 · 不以无关新闻填充栏目"}
                    </div>
                  )}
                </section>
              );
            })}
          </section>
        ))
      )}
    </>
  );
}
