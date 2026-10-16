import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { errorText, request } from "./api";
import type { Health, Job } from "./types";
import { AppContext } from "./state";
import { ErrorBox, Icon } from "./components/ui";
import { Dashboard } from "./pages/Dashboard";
import { NewsDetail } from "./pages/NewsDetail";
import { History } from "./pages/History";
import { Sources } from "./pages/Sources";
import { Search } from "./pages/Search";
import { Bookmarks } from "./pages/Bookmarks";
import { Account } from "./pages/Account";
import { useAuth } from "./auth";

export default function App() {
  const { user } = useAuth();
  const [health, setHealth] = useState<Health | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [connectionError, setConnectionError] = useState("");
  const [actionError, setActionError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [tokenOpen, setTokenOpen] = useState(false);
  const [token, setToken] = useState("");
  useEffect(() => {
    let active = true;
    let busy = false;
    async function poll() {
      if (busy) return;
      busy = true;
      try {
        const [h, j] = await Promise.all([
          request<Health>("/health"),
          request<Job | null>("/runs/latest"),
        ]);
        if (active) {
          setHealth(h);
          setJob(j);
          setConnectionError("");
        }
      } catch {
        if (active)
          setConnectionError("暂时无法连接服务，请检查后端是否已启动。");
      } finally {
        busy = false;
      }
    }
    void poll();
    const timer = setInterval(() => void poll(), 4000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  const running = job?.status === "queued" || job?.status === "running";
  async function generate() {
    setSubmitting(true);
    setActionError("");
    try {
      const data = await request<Job>("/runs", {
        method: "POST",
        headers: token ? { "X-Admin-Token": token } : {},
      });
      setJob(data);
      setTokenOpen(false);
      setToken("");
    } catch (e) {
      setActionError(errorText(e));
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <AppContext.Provider value={{ health, job }}>
      <a className="skip-link" href="#main">
        跳到主要内容
      </a>
      <div className="app-shell">
        <aside className="sidebar">
          <Link to="/" className="brand">
            <span className="brand-mark">
              N<span>·</span>
            </span>
            <span>
              <strong>DAILY NEWS</strong>
              <small>智能每日新闻总结助手</small>
            </span>
          </Link>
          <div className="nav-label">我的新闻空间</div>
          <nav aria-label="主导航">
            <NavLink end to="/">
              <Icon name="grid" />
              每日简报
            </NavLink>
            <NavLink to="/history">
              <Icon name="history" />
              历史日报
            </NavLink>
            <NavLink to="/search">
              <Icon name="search" />
              搜索新闻
            </NavLink>
            <NavLink to="/bookmarks">
              <Icon name="bookmark" />
              我的收藏
            </NavLink>
            <NavLink to="/account">
              <Icon name="user" />
              我的账号
            </NavLink>
            <NavLink to="/sources">
              <Icon name="source" />
              新闻来源
            </NavLink>
          </nav>
          <div className="sidebar-note">
            <div className="pulse-dot" />
            <strong>每天，保持了解</strong>
            <p>
              中国 · 国际
              <br />
              政治 · 金融 · 科技 · AI
            </p>
            <span>WEB + ANDROID / 04</span>
          </div>
          <div className="sidebar-footer">
            少一点信息噪音
            <br />
            多一点清晰理解
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <div className="topbar-label">
              环球早报 <span>/</span> DAILY BRIEF
            </div>
            <div className="topbar-actions">
              <Link className="account-link" to="/account">
                {user ? user.display_name : "登录 / 注册"}
              </Link>
              <span
                className={`service-status ${health?.worker_online ? "online" : ""}`}
              >
                <i />
                {health?.worker_online ? "自动任务在线" : "自动任务离线"}
              </span>
              <button
                className="primary-button"
                disabled={
                  !!running ||
                  submitting ||
                  !health?.report_due ||
                  !!connectionError ||
                  !user
                }
                title={user ? "生成今日早报" : "登录后可更新早报"}
                onClick={() =>
                  health?.token_required ? setTokenOpen(true) : void generate()
                }
              >
                <Icon name="refresh" size={16} />
                {running ? "正在生成…" : submitting ? "正在提交…" : "更新早报"}
              </button>
            </div>
          </header>
          <main id="main">
            {connectionError && <ErrorBox message={connectionError} />}{" "}
            {actionError && <ErrorBox message={actionError} />}{" "}
            {tokenOpen && (
              <form
                className="token-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void generate();
                }}
              >
                <label>
                  管理口令
                  <input
                    type="password"
                    autoComplete="off"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                    required
                  />
                </label>
                <button
                  type="submit"
                  className="primary-button"
                  disabled={submitting}
                >
                  提交任务
                </button>
                <button
                  type="button"
                  className="text-button"
                  onClick={() => {
                    setTokenOpen(false);
                    setToken("");
                  }}
                >
                  取消
                </button>
              </form>
            )}
            {health && !health.worker_online && !connectionError && (
              <div className="notice">
                自动任务进程当前离线。已保存的日报仍可阅读，新任务将在 worker
                启动后执行。
              </div>
            )}
            {job && (running || job.status === "failed") && (
              <div
                role="status"
                className={`notice ${job.status === "failed" ? "notice-error" : "notice-progress"}`}
              >
                <span>
                  {job.status === "failed" ? "最近任务失败：" : ""}
                  {job.message}
                </span>
                <Link to="/sources">查看来源</Link>
              </div>
            )}
            <Routes>
              <Route path="/search" element={<Search />} />
              <Route path="/bookmarks" element={<Bookmarks />} />
              <Route path="/account" element={<Account />} />
              <Route path="/" element={<Dashboard />} />
              <Route path="/history" element={<History />} />
              <Route path="/sources" element={<Sources />} />
              <Route path="/news/:id" element={<NewsDetail />} />
              <Route
                path="*"
                element={
                  <div className="empty">
                    <h1>页面不存在</h1>
                    <Link to="/">返回首页</Link>
                  </div>
                }
              />
            </Routes>
            <footer className="page-footer">
              <span>AI Daily News Assistant</span>
              <span>来源可追溯 · 事实与推断分开展示</span>
            </footer>
          </main>
        </div>
      </div>
    </AppContext.Provider>
  );
}
