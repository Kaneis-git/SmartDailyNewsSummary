import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth";
import { Account } from "../pages/Account";
import { Search } from "../pages/Search";
import { Bookmarks } from "../pages/Bookmarks";
const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
it("visitor receives login form after session check returns 401", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => json({ detail: "请先登录" }, 401)),
  );
  render(
    <AuthProvider>
      <Account />
    </AuthProvider>,
  );
  expect(await screen.findByRole("heading", { name: "欢迎回来" })).toBeTruthy();
  expect(screen.queryByText("正在读取账号…")).toBeNull();
});
it("registration submits web credentials, loads user, logout clears private state", async () => {
  let signedIn = false;
  let registered: Record<string, unknown> | null = null;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, init?: RequestInit) => {
      if (path.endsWith("/register")) {
        registered = JSON.parse(String(init?.body));
        signedIn = true;
        return json(
          { user: { id: 1, username: "reader", display_name: "读者" } },
          201,
        );
      }
      if (path.endsWith("/logout")) {
        signedIn = false;
        return json({ ok: true });
      }
      if (path.endsWith("/ids")) return json([7]);
      return signedIn
        ? json({ id: 1, username: "reader", display_name: "读者" })
        : json({ detail: "请先登录" }, 401);
    }),
  );
  const user = userEvent.setup();
  render(
    <AuthProvider>
      <Account />
    </AuthProvider>,
  );
  await screen.findByText("欢迎回来");
  await user.click(screen.getByText("还没有账号？创建账号"));
  await user.type(screen.getByLabelText("用户名"), "reader");
  await user.type(screen.getByLabelText("昵称"), "读者");
  await user.type(screen.getByLabelText("密码"), "Long-Password-123");
  await user.click(screen.getByRole("button", { name: "注册并登录" }));
  await screen.findByRole("heading", { name: "我的账号" });
  expect(registered).toMatchObject({
    username: "reader",
    display_name: "读者",
    platform: "web",
  });
  expect(localStorage.length).toBe(0);
  await user.click(screen.getByText("退出当前设备"));
  expect(await screen.findByText("欢迎回来")).toBeTruthy();
});
it("unauthenticated bookmarks show login entry", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => json({ detail: "请先登录" }, 401)),
  );
  render(
    <MemoryRouter>
      <AuthProvider>
        <Bookmarks />
      </AuthProvider>
    </MemoryRouter>,
  );
  expect(await screen.findByText("登录后查看收藏")).toBeTruthy();
});
it("search sends Chinese keyword and region filter", async () => {
  const urls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) => {
      urls.push(path);
      return path.includes("/search")
        ? json({ items: [], total: 0, page: 1, page_size: 20 })
        : json({ detail: "请先登录" }, 401);
    }),
  );
  render(
    <MemoryRouter>
      <AuthProvider>
        <Search />
      </AuthProvider>
    </MemoryRouter>,
  );
  const user = userEvent.setup();
  await screen.findByText("暂未找到匹配新闻");
  await user.type(screen.getByLabelText("搜索关键词"), "人工智能");
  await user.selectOptions(screen.getByLabelText("地区"), "china");
  await user.selectOptions(screen.getByLabelText("领域"), "ai");
  await user.click(screen.getByRole("button", { name: "搜索" }));
  await waitFor(() =>
    expect(
      urls.some(
        (v) =>
          v.includes("region=china") &&
          v.includes("category=ai") &&
          decodeURIComponent(v).includes("人工智能"),
      ),
    ).toBe(true),
  );
});
