import { useEffect, useState } from "react";
import { errorText, request } from "../api";
import type { Source } from "../types";
import { useApp } from "../state";
import { ErrorBox, regionNames } from "../components/ui";

export function Sources() {
  const { job } = useApp();
  const [sources, setSources] = useState<Source[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    setError("");
    request<Source[]>("/sources")
      .then((data) => {
        if (active) setSources(data);
      })
      .catch((e) => {
        if (active) setError(errorText(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [job?.status, job?.source_results.length, retry]);
  return (
    <>
      <div className="page-heading">
        <div>
          <div className="eyebrow">TRACE EVERY STORY</div>
          <h1>新闻来源</h1>
          <p>每一条摘要，都有可追溯的出处。</p>
        </div>
      </div>
      <div className="notice subtle">
        以下显示最近一次任务的来源状态。可读取的来源，也可能没有本期时间范围内的新闻。
      </div>
      {error && (
        <ErrorBox message={error} retry={() => setRetry((r) => r + 1)} />
      )}{" "}
      {loading && (
        <div className="loading" role="status">
          正在读取来源…
        </div>
      )}
      <div className="source-grid">
        {sources.map((source) => (
          <article className="source-card" key={source.id}>
            <div className="source-card-top">
              <span className="source-letter">
                {source.name.startsWith("BBC") ? "B" : "中"}
              </span>
              <span
                className={`badge ${source.last_result?.status === "error" ? "badge-error" : "badge-neutral"}`}
              >
                {!source.enabled
                  ? "已停用"
                  : source.last_result?.status === "ok"
                    ? "已读取"
                    : source.last_result?.status === "error"
                      ? "暂不可用"
                      : "尚未采集"}
              </span>
            </div>
            <h2>{source.name}</h2>
            <p>{regionNames[source.region_hint]} · RSS</p>
            <div className="source-status">
              {source.last_result?.message || "生成日报后，将显示采集结果。"}
              {source.last_result?.status === "ok" && (
                <small>
                  读取 {source.last_result.seen} 条 · 符合时间条件{" "}
                  {source.last_result.accepted} 条 · 过滤{" "}
                  {source.last_result.skipped} 条
                </small>
              )}
            </div>
            <a
              className="text-button"
              href={source.feed_url}
              target="_blank"
              rel="noopener noreferrer"
            >
              查看 RSS 来源 ↗
            </a>
          </article>
        ))}
      </div>
      <p className="muted source-footnote">
        来源栏目仅作为预分类参考；新闻按事件主体与主题归类。源的访问状况取决于本机网络。
      </p>
    </>
  );
}
