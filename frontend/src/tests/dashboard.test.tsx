import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "../pages/Dashboard";
import type { Category } from "../types";

vi.mock("../components/BookmarkButton", () => ({ BookmarkButton: () => null }));
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

function serveReport(legacy = false) {
  const items = ["china", "international"].flatMap((region, ri) =>
    (["politics", "finance", "technology", ...(legacy ? [] : ["ai"])] as Category[]).flatMap((category, ci) =>
      Array.from({ length: 10 }, (_, i) => ({
        id: ri * 100 + ci * 10 + i, title: `${region}-${category}-${i + 1}`,
        source_name: "测试来源", published_at: "2026-10-11T20:00:00Z", report_date: "2026-10-12",
        analysis_status: "extractive", analysis: { region, category, summary: "测试摘要", importance: 3, tags: [] },
      })),
    ));
  const coverage = Object.fromEntries(items.map(i => [`${i.analysis.region}.${i.analysis.category}`, 10]));
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
    date: "2026-10-12", items, coverage, total: items.length, status: "ready", source_results: [],
    window_start: "2026-10-11T00:00:00Z", window_end: "2026-10-12T00:00:00Z", generated_at: "2026-10-12T00:01:00Z",
  }), { headers: { "Content-Type": "application/json" } })));
  return render(<MemoryRouter initialEntries={["/?date=2026-10-12"]}><Dashboard /></MemoryRouter>);
}

it("shows all 80 items and independently filters AI and region", async () => {
  serveReport();
  await screen.findByText("china-ai-10");
  expect(screen.getAllByRole("article")).toHaveLength(80);
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "AI 人工智能" }));
  expect(screen.getAllByRole("article")).toHaveLength(20);
  expect(screen.queryByText("china-technology-1")).toBeNull();
  await user.click(screen.getByRole("button", { name: "中国新闻" }));
  expect(screen.getAllByRole("article")).toHaveLength(10);
  expect(screen.queryByText("international-ai-1")).toBeNull();
});

it("reads old reports without inventing historical AI items", async () => {
  serveReport(true);
  expect(await screen.findAllByText("此历史日报生成时尚未开设 AI 栏目")).toHaveLength(2);
  expect(screen.getAllByRole("article")).toHaveLength(60);
});
