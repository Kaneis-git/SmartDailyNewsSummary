import type { ReactNode } from "react";
import type { Category } from "../types";

export const regionNames = { china: "中国新闻", international: "国际新闻" };
export const categoryNames: Record<Category, string> = {
  politics: "时事政治",
  finance: "金融经济",
  technology: "科技发展",
  ai: "AI 人工智能",
};
export const reportStatus = {
  ready: "已生成",
  partial: "部分收录",
  empty: "暂无收录",
};

export function Icon({
  name,
  size = 19,
}: {
  name:
    | "grid"
    | "history"
    | "source"
    | "arrow"
    | "refresh"
    | "download"
    | "search"
    | "bookmark"
    | "user";
  size?: number;
}) {
  const paths = {
    search: "M10 3a7 7 0 1 0 0 14 7 7 0 0 0 0-14 M15 15l6 6",
    bookmark: "M5 3h14v18l-7-4-7 4V3z",
    user: "M12 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M4 21v-3a8 8 0 0 1 16 0v3",
    grid: "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
    history:
      "M4 3h13a2 2 0 0 1 2 2v16H6a2 2 0 0 1-2-2V3z M4 17h15 M8 7h7 M8 11h5",
    source:
      "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M3 12h18 M12 3c-5 5-5 13 0 18 M12 3c5 5 5 13 0 18",
    arrow: "M5 12h14 M13 6l6 6-6 6",
    refresh:
      "M20 7v5h-5 M4 17v-5h5 M5.5 7a7.5 7.5 0 0 1 13-2l1.5 2 M18.5 17a7.5 7.5 0 0 1-13 2L4 17",
    download: "M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5",
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={paths[name]} />
    </svg>
  );
}
export function Empty({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <span className="empty-icon">
        <Icon name="history" size={30} />
      </span>
      <h2>{title}</h2>
      <div>{children}</div>
    </div>
  );
}
export function AnalysisBadge({ status }: { status: string }) {
  return (
    <span className={`badge ${status === "ai" ? "badge-ai" : "badge-neutral"}`}>
      {status === "ai"
        ? "AI 已分析"
        : status === "fallback"
          ? "分析降级"
          : "来源摘要"}
    </span>
  );
}
export function ErrorBox({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="notice notice-error" role="alert">
      <span>{message}</span>
      {retry && (
        <button className="text-button" onClick={retry}>
          重试
        </button>
      )}
    </div>
  );
}
