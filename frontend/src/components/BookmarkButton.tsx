import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth";
import { errorText } from "../api";
import type { NewsItem } from "../types";
export function BookmarkButton({ item }: { item: NewsItem }) {
  const { user, saved, toggle } = useAuth();
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  if (!user)
    return (
      <Link className="text-button" to="/account">
        登录收藏
      </Link>
    );
  return (
    <span className="bookmark-action">
      <button
        className={`text-button ${saved.has(item.id) ? "is-saved" : ""}`}
        disabled={busy}
        aria-pressed={saved.has(item.id)}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            await toggle(item);
          } catch (e) {
            setError(errorText(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "保存中…" : saved.has(item.id) ? "★ 已收藏" : "☆ 收藏"}
      </button>
      {error && <small role="alert">{error}</small>}
    </span>
  );
}
