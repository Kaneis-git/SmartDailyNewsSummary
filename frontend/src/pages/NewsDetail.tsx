import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { dateTime, errorText, request } from "../api";
import type { NewsItem } from "../types";
import {
  AnalysisBadge,
  categoryNames,
  ErrorBox,
  regionNames,
} from "../components/ui";
import { NewsCard } from "../components/NewsCard";
import { BookmarkButton } from "../components/BookmarkButton";
import type { SavedNews } from "./Bookmarks";

export function NewsDetail() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const day = params.get("date");
  const saved = params.get("saved") === "1";
  const [item, setItem] = useState<NewsItem | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setItem(null);
    setError("");
    (saved
      ? request<SavedNews>(`/bookmarks/${id}`).then((data) => data.news)
      : request<NewsItem>(
          `/news/${id}${day ? "?report_date=" + encodeURIComponent(day) : ""}`,
        )
    )
      .then((data) => {
        if (active) setItem(data);
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      });
    return () => {
      active = false;
    };
  }, [id, day, saved]);
  if (error) return <ErrorBox message={error} />;
  if (!item)
    return (
      <div className="loading" role="status">
        正在读取新闻…
      </div>
    );
  const a = item.analysis;
  return (
    <div className="detail-page">
      <Link className="back-link" to={`/?date=${item.report_date}`}>
        ← 返回本期日报
      </Link>
      <article className="detail-article">
        <div className="eyebrow">
          {regionNames[a.region]} / {categoryNames[a.category]}
        </div>
        <h1>{item.title}</h1>
        <div className="detail-meta">
          <span>{item.source_name}</span>
          <span>{dateTime(item.published_at)} 发布</span>
          <AnalysisBadge status={item.analysis_status} />
        </div>
        <div className="detail-source">
          <span>原始标题：{item.original_title}</span>
          <a href={item.url} target="_blank" rel="noopener noreferrer">
            阅读原文 ↗
          </a>
        </div>
        <BookmarkButton item={item} />
        {saved && <p className="muted">当前展示收藏时保存的版本。</p>}
        <section className="summary-box">
          <div className="eyebrow">
            {item.analysis_status === "ai" ? "AI 内容摘要" : "来源摘要"}
          </div>
          <p>{a.summary}</p>
        </section>
        <section>
          <h2>原文摘要</h2>
          <p className="original-excerpt">
            {item.original_excerpt || "该来源未提供摘要，请打开原文阅读。"}
          </p>
          <p className="muted">来自 RSS 的公开摘要，不代表全文。</p>
        </section>
        {a.facts.length > 0 && (
          <section>
            <h2>关键事实</h2>
            <ul className="facts">
              {a.facts.map((fact, i) => (
                <li key={i}>{fact}</li>
              ))}
            </ul>
          </section>
        )}
        <section>
          <h2>
            为什么值得关注{" "}
            <span className="importance">{"★".repeat(a.importance)}</span>
          </h2>
          <p>{a.importance_reason}</p>
          {a.why_important && <p>{a.why_important}</p>}
          <p className="muted">
            星级用于阅读排序，不表示事实可信度或投资收益概率。
          </p>
        </section>
        <section>
          <h2>影响分析</h2>
          {item.analysis_status === "ai" ? (
            <>
              <p className="muted">
                以下是基于当前来源的分析与条件情景，请结合原文判断。
              </p>
              <div className="impact-grid">
                {(
                  [
                    ["people_impact", "对普通人的影响"],
                    ["market_impact", "对市场的影响"],
                    ["short_term", "短期可能发展"],
                    ["long_term", "长期可能发展"],
                  ] as const
                ).map(([key, name]) => (
                  <div className="impact-card" key={key}>
                    <h3>{name}</h3>
                    <p>{a[key] || "当前来源不足以支持这一判断。"}</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="notice">
              本条尚无 AI 影响分析。来源摘要不会被当作预测展示。
            </div>
          )}
        </section>
        {a.industries.length > 0 && (
          <section>
            <h2>相关行业</h2>
            <div className="tag-list">
              {a.industries.map((tag, i) => (
                <span key={i}>{tag}</span>
              ))}
            </div>
          </section>
        )}
        <section className="limitations">
          <h2>信息局限与核对提示</h2>
          <ul>
            {a.limitations.map((value, i) => (
              <li key={i}>{value}</li>
            ))}
          </ul>
          <a
            className="text-button"
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            打开原始来源核对 ↗
          </a>
        </section>
      </article>
      {!!item.related?.length && (
        <section>
          <div className="section-heading">
            <h2>本期同类新闻</h2>
          </div>
          <p className="muted">按领域关联，不代表同一事件或交叉证实。</p>
          <div className="news-grid">
            {item.related.map((row) => (
              <NewsCard key={row.id} item={row} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
