import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { errorText, request } from "../api";
import type { NewsItem } from "../types";
import { ErrorBox, Empty, categoryNames } from "../components/ui";
import { NewsCard } from "../components/NewsCard";
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export function Pager({
  page,
  total,
  onPage,
}: {
  page: number;
  total: number;
  onPage: (p: number) => void;
}) {
  return total > 20 ? (
    <div className="pager">
      <button
        className="secondary-button"
        disabled={page === 1}
        onClick={() => onPage(page - 1)}
      >
        上一页
      </button>
      <span>
        第 {page} / {Math.ceil(total / 20)} 页
      </span>
      <button
        className="secondary-button"
        disabled={page * 20 >= total}
        onClick={() => onPage(page + 1)}
      >
        下一页
      </button>
    </div>
  ) : null;
}
export function Search() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<Page<NewsItem> | null>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false);
  const query = params.toString();
  useEffect(() => {
    const abort = new AbortController();
    setLoading(true);
    setError("");
    request<Page<NewsItem>>("/search?" + query, { signal: abort.signal })
      .then(setData)
      .catch((e) => {
        if (!abort.signal.aborted) setError(errorText(e));
      })
      .finally(() => {
        if (!abort.signal.aborted) setLoading(false);
      });
    return () => abort.abort();
  }, [query]);
  return (
    <>
      <div className="eyebrow">EXPLORE THE ARCHIVE</div>
      <h1>搜索新闻</h1>
      <p className="muted">检索已收录日报的标题与摘要，按新闻去重。</p>
      <form
        key={query}
        className="search-form"
        onSubmit={(e) => {
          e.preventDefault();
          const values = new FormData(e.currentTarget),
            next = new URLSearchParams();
          values.forEach((v, k) => {
            if (String(v).trim()) next.set(k, String(v).trim());
          });
          setParams(next);
        }}
      >
        <label className="search-keyword">
          关键词
          <input
            name="q"
            aria-label="搜索关键词"
            placeholder="例如：人工智能、货币政策"
            maxLength={100}
            defaultValue={params.get("q") || ""}
          />
        </label>
        <label>
          地区
          <select name="region" defaultValue={params.get("region") || ""}>
            <option value="">全部地区</option>
            <option value="china">中国新闻</option>
            <option value="international">国际新闻</option>
          </select>
        </label>
        <label>
          领域
          <select name="category" defaultValue={params.get("category") || ""}>
            <option value="">全部领域</option>
            {Object.entries(categoryNames).map(([value, name]) => (
              <option key={value} value={value}>{name}</option>
            ))}
          </select>
        </label>
        <label>
          开始日期
          <input
            type="date"
            name="date_from"
            defaultValue={params.get("date_from") || ""}
          />
        </label>
        <label>
          结束日期
          <input
            type="date"
            name="date_to"
            defaultValue={params.get("date_to") || ""}
          />
        </label>
        <button className="primary-button">搜索</button>
      </form>
      {error && <ErrorBox message={error} />}{" "}
      {loading ? (
        <div className="loading" role="status">
          正在搜索…
        </div>
      ) : (
        data && (
          <>
            <p className="result-count" role="status">
              找到 {data.total} 条新闻
            </p>
            {data.total ? (
              <div className="news-grid">
                {data.items.map((item) => (
                  <NewsCard key={item.id} item={item} />
                ))}
              </div>
            ) : (
              <Empty title="暂未找到匹配新闻">
                试试更短的关键词或扩大日期范围。
              </Empty>
            )}
            <Pager
              page={data.page}
              total={data.total}
              onPage={(p) => {
                const next = new URLSearchParams(params);
                next.set("page", String(p));
                setParams(next);
              }}
            />
          </>
        )
      )}
    </>
  );
}
