import { useState } from "react";
import { useAuth } from "../auth";
import { errorText, request } from "../api";
import { ErrorBox } from "../components/ui";
export function Account() {
  const { user, loading, refresh, logout } = useAuth();
  const [register, setRegister] = useState(false),
    [username, setUsername] = useState(""),
    [displayName, setDisplayName] = useState(""),
    [password, setPassword] = useState(""),
    [current, setCurrent] = useState(""),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function action(fn: () => Promise<void>) {
    setError("");
    setMessage("");
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
      setPassword("");
      setCurrent("");
    }
  }
  if (loading) return <div className="loading">正在读取账号…</div>;
  return (
    <div className="account-page">
      <div className="eyebrow">YOUR NEWS SPACE</div>
      <h1>{user ? "我的账号" : register ? "创建你的新闻空间" : "欢迎回来"}</h1>
      <p className="muted">Web 与 Android 共用收藏和私人标签。</p>
      {error && <ErrorBox message={error} />}{" "}
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      {user ? (
        <>
          <section className="account-card">
            <h2>{user.display_name}</h2>
            <p>@{user.username}</p>
            <div className="inline-actions">
              <button
                className="secondary-button"
                disabled={busy}
                onClick={() => void action(() => logout())}
              >
                退出当前设备
              </button>
              <button
                className="text-button"
                disabled={busy}
                onClick={() => void action(() => logout(true))}
              >
                退出所有设备
              </button>
            </div>
          </section>
          <form
            className="account-card form-stack"
            onSubmit={(e) => {
              e.preventDefault();
              void action(async () => {
                await request("/auth/password", {
                  method: "POST",
                  body: JSON.stringify({
                    current_password: current,
                    new_password: password,
                  }),
                });
                await refresh();
                setMessage("密码已更新，请重新登录。");
              });
            }}
          >
            <h2>修改密码</h2>
            <label>
              当前密码
              <input
                type="password"
                autoComplete="current-password"
                required
                maxLength={128}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
              />
            </label>
            <label>
              新密码
              <input
                type="password"
                autoComplete="new-password"
                minLength={10}
                maxLength={128}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </label>
            <small className="muted">
              至少 10 位。修改后各设备需重新登录。
            </small>
            <button className="primary-button" disabled={busy}>
              更新密码
            </button>
          </form>
        </>
      ) : (
        <form
          className="account-card form-stack"
          onSubmit={(e) => {
            e.preventDefault();
            void action(async () => {
              await request("/auth/" + (register ? "register" : "login"), {
                method: "POST",
                body: JSON.stringify({
                  username,
                  password,
                  platform: "web",
                  ...(register ? { display_name: displayName } : {}),
                }),
              });
              await refresh();
              setRegister(false);
            });
          }}
        >
          <label>
            用户名
            <input
              autoComplete="username"
              required
              minLength={3}
              maxLength={32}
              pattern="[A-Za-z0-9_]+"
              placeholder="字母、数字或下划线，3–32 位"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          {register && (
            <label>
              昵称
              <input
                required
                maxLength={60}
                autoComplete="nickname"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </label>
          )}
          <label>
            密码
            <input
              type="password"
              autoComplete={register ? "new-password" : "current-password"}
              required
              minLength={10}
              maxLength={128}
              placeholder="至少 10 位"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button className="primary-button" disabled={busy}>
            {busy ? "处理中…" : register ? "注册并登录" : "登录"}
          </button>
          <button
            className="text-button"
            type="button"
            onClick={() => {
              setRegister(!register);
              setError("");
              setPassword("");
            }}
          >
            {register ? "已有账号？去登录" : "还没有账号？创建账号"}
          </button>
        </form>
      )}
    </div>
  );
}
