export type Region = "china" | "international";
export type Category = "politics" | "finance" | "technology" | "ai";
export interface Analysis {
  headline: string;
  region: Region;
  category: Category;
  summary: string;
  facts: string[];
  importance: number;
  importance_reason: string;
  why_important: string;
  people_impact: string;
  market_impact: string;
  short_term: string;
  long_term: string;
  industries: string[];
  tags: string[];
  limitations: string[];
}
export interface NewsItem {
  id: number;
  original_title: string;
  title: string;
  source_name: string;
  source_id: string;
  url: string;
  published_at: string;
  original_excerpt: string;
  analysis_status: "ai" | "extractive" | "fallback";
  analysis: Analysis;
  report_date: string;
  related?: NewsItem[];
}
export interface SourceResult {
  id: string;
  name: string;
  status: string;
  seen: number;
  accepted: number;
  skipped: number;
  message: string;
}
export interface Report {
  date: string;
  window_start: string;
  window_end: string;
  generated_at: string;
  status: "ready" | "partial" | "empty";
  coverage: Record<string, number>;
  total: number;
  source_results: SourceResult[];
  items: NewsItem[];
}
export interface Job {
  id: string;
  report_date: string;
  status: "queued" | "running" | "succeeded" | "failed";
  message: string;
  created_at: string;
  finished_at: string | null;
  source_results: SourceResult[];
}
export interface Health {
  max_per_section: number;
  status: string;
  worker_online: boolean;
  ai_enabled: boolean;
  ai_model: string | null;
  timezone: string;
  schedule: string;
  today: string;
  report_due: boolean;
  token_required: boolean;
}
export interface Source {
  id: string;
  name: string;
  feed_url: string;
  region_hint: Region;
  category_hint: string;
  enabled: boolean;
  last_result: SourceResult | null;
}
