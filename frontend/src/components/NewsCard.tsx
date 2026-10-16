import { Link } from "react-router-dom";
import type { NewsItem } from "../types";
import { dateTime } from "../api";
import { AnalysisBadge, Icon } from "./ui";
import { BookmarkButton } from "./BookmarkButton";

export function NewsCard({
  item,
  featured = false,
  savedSnapshot = false,
}: {
  item: NewsItem;
  featured?: boolean;
  savedSnapshot?: boolean;
}) {
  const detailUrl = `/news/${item.id}?${savedSnapshot ? "saved=1" : "date=" + item.report_date}`;
  return (
    <article className={`news-card ${featured ? "featured" : ""}`}>
      <div className="card-eyebrow">
        <span>{featured ? "重点关注" : item.source_name}</span>
        <span
          className="importance"
          aria-label={`重要程度 ${item.analysis.importance} 星，共 5 星`}
          title={item.analysis.importance_reason}
        >
          {"★".repeat(item.analysis.importance)}
          <span>{"☆".repeat(5 - item.analysis.importance)}</span>
        </span>
      </div>
      <h3>
        <Link to={detailUrl}>{item.title}</Link>
      </h3>
      <p className="card-summary">{item.analysis.summary}</p>
      <div className="card-tags">
        {item.analysis.tags.slice(0, 3).map((tag, index) => (
          <span key={index}>#{tag}</span>
        ))}
      </div>
      <div className="card-footer">
        <div>
          <AnalysisBadge status={item.analysis_status} />
          <span className="card-time">
            {dateTime(item.published_at, false)}
          </span>
        </div>
        <Link
          className="read-link"
          aria-label={`阅读 ${item.title}`}
          to={detailUrl}
        >
          阅读 <Icon name="arrow" size={16} />
        </Link>
      </div>
      <BookmarkButton item={item} />
      {featured && (
        <div className="featured-source">
          {item.source_name} · {dateTime(item.published_at)}
        </div>
      )}
    </article>
  );
}
