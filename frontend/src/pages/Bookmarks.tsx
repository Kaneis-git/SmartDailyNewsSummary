import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { errorText, request } from "../api";
import type { NewsItem } from "../types";
import { ErrorBox, Empty } from "../components/ui";
import { NewsCard } from "../components/NewsCard";
import { Pager } from "./Search";
import type { Page } from "./Search";
export interface Tag {
  id: number;
  name: string;
}
export interface SavedNews {
  news: NewsItem;
  tags: Tag[];
  saved_at: string;
}
function TagEditor({
  row,
  tags,
  reload,
}: {
  row: SavedNews;
  tags: Tag[];
  reload: () => void;
}) {
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="saved-tags">
      <span>我的标签</span>
      {tags.length ? (
        tags.map((t) => (
          <label key={t.id}>
            <input
              type="checkbox"
              disabled={busy}
              checked={row.tags.some((x) => x.id === t.id)}
              onChange={async (e) => {
                const ids = new Set(row.tags.map((x) => x.id));
                if (e.target.checked) ids.add(t.id);
                else ids.delete(t.id);
                setBusy(true);
                try {
                  await request(`/bookmarks/${row.news.id}`, {
                    method: "PUT",
                    body: JSON.stringify({ tag_ids: [...ids] }),
                  });
                  reload();
                  setError("");
                } catch (e) {
                  setError(errorText(e));
                } finally {
                  setBusy(false);
                }
              }}
            />
            {t.name}
          </label>
        ))
      ) : (
        <small>先在上方创建标签</small>
      )}
      {error && <small role="alert">{error}</small>}
    </div>
  );
}
export function Bookmarks() {
  const { user, saved } = useAuth();
  const [data, setData] = useState<Page<SavedNews> | null>(null),
    [tags, setTags] = useState<Tag[]>([]),
    [q, setQ] = useState(""),
    [draft, setDraft] = useState(""),
    [tagId, setTagId] = useState(""),
    [page, setPage] = useState(1),
    [tick, setTick] = useState(0),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [name, setName] = useState(""),
    [editing, setEditing] = useState<number | null>(null),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!user) {
      setData(null);
      setTags([]);
      return;
    }
    let active = true;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ q, page: String(page) });
    if (tagId) params.set("tag_id", tagId);
    Promise.all([
      request<Page<SavedNews>>("/bookmarks?" + params),
      request<Tag[]>("/tags"),
    ])
      .then(([d, t]) => {
        if (active) {
          setData(d);
          setTags(t);
          if (page > 1 && d.items.length === 0) setPage(page - 1);
        }
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
  }, [user, q, tagId, page, tick, saved]);
  async function editTag(remove?: number) {
    setError("");
    setBusy(true);
    try {
      await request(
        remove ? `/tags/${remove}` : editing ? `/tags/${editing}` : "/tags",
        {
          method: remove ? "DELETE" : editing ? "PATCH" : "POST",
          ...(!remove ? { body: JSON.stringify({ name }) } : {}),
        },
      );
      setName("");
      setEditing(null);
      if (String(remove) === tagId) setTagId("");
      setTick((t) => t + 1);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  if (!user)
    return (
      <Empty title="把重要新闻留下来">
        <Link to="/account" className="primary-button">
          登录后查看收藏
        </Link>
      </Empty>
    );
  return (
    <>
      <div className="eyebrow">SAVED FOR LATER</div>
      <h1>我的收藏</h1>
      <p className="muted">
        私人标签帮助整理关注的议题。收藏保留保存时的新闻版本。
      </p>
      {error && <ErrorBox message={error} />}
      <section className="tag-manager">
        <div className="inline-actions">
          {tags.map((t) => (
            <span className="editable-tag" key={t.id}>
              <button
                className="text-button"
                onClick={() => {
                  setEditing(t.id);
                  setName(t.name);
                }}
                title="重命名"
              >
                {t.name}
              </button>
              <button
                disabled={busy}
                aria-label={`删除标签 ${t.name}，保留新闻`}
                onClick={() => void editTag(t.id)}
              >
                ×
              </button>
            </span>
          ))}
        </div>
        <form
          className="inline-actions"
          onSubmit={(e) => {
            e.preventDefault();
            void editTag();
          }}
        >
          <input
            aria-label="标签名称"
            required
            maxLength={24}
            placeholder="新标签，例如：本周关注"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <button className="secondary-button" disabled={busy}>
            {editing ? "保存名称" : "创建标签"}
          </button>
          {editing && (
            <button
              type="button"
              className="text-button"
              onClick={() => {
                setEditing(null);
                setName("");
              }}
            >
              取消
            </button>
          )}
        </form>
        <small className="muted">
          点击标签名可重命名；删除标签会保留新闻。
        </small>
      </section>
      <form
        className="search-form"
        onSubmit={(e) => {
          e.preventDefault();
          setQ(draft);
          setPage(1);
        }}
      >
        <input
          aria-label="搜索收藏"
          placeholder="在收藏中搜索"
          maxLength={100}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <select
          aria-label="标签筛选"
          value={tagId}
          onChange={(e) => {
            setTagId(e.target.value);
            setPage(1);
          }}
        >
          <option value="">全部标签</option>
          {tags.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
        <button className="primary-button">筛选</button>
      </form>
      {loading ? (
        <div className="loading">正在读取收藏…</div>
      ) : (
        data && (
          <>
            <p className="result-count">{data.total} 条收藏</p>
            {data.total ? (
              <div className="news-grid">
                {data.items.map((row) => (
                  <div className="saved-card" key={row.news.id}>
                    <NewsCard item={row.news} savedSnapshot />
                    <TagEditor
                      row={row}
                      tags={tags}
                      reload={() => setTick((t) => t + 1)}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <Empty title="这里还没有新闻">
                在新闻卡片上点击收藏，或调整筛选条件。
              </Empty>
            )}
            <Pager page={page} total={data.total} onPage={setPage} />
          </>
        )
      )}
    </>
  );
}
