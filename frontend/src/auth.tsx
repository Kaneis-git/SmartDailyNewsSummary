import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  useCallback,
} from "react";
import type { ReactNode } from "react";
import { ApiError, request } from "./api";
import type { NewsItem } from "./types";
export interface User {
  id: number;
  username: string;
  display_name: string;
}
interface AuthState {
  user: User | null;
  loading: boolean;
  saved: Set<number>;
  refresh: () => Promise<void>;
  logout: (all?: boolean) => Promise<void>;
  toggle: (item: NewsItem) => Promise<void>;
}
const Context = createContext<AuthState | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [saved, setSaved] = useState(new Set<number>());
  const epoch = useRef(0);
  const refresh = useCallback(async () => {
    const version = ++epoch.current;
    try {
      const me = await request<User>("/auth/me");
      const ids = await request<number[]>("/bookmarks/ids");
      if (version === epoch.current) {
        setUser(me);
        setSaved(new Set(ids));
      }
    } catch (e) {
      if (version === epoch.current) {
        setUser(null);
        setSaved(new Set());
      }
      if (!(e instanceof ApiError && e.status === 401)) throw e;
    } finally {
      if (version === epoch.current) setLoading(false);
    }
  }, []);
  useEffect(() => {
    void refresh().catch(() => {});
    const expired = () => {
      epoch.current++;
      setUser(null);
      setSaved(new Set());
      setLoading(false);
    };
    window.addEventListener("session-expired", expired);
    return () => window.removeEventListener("session-expired", expired);
  }, [refresh]);
  async function logout(all = false) {
    await request("/auth/" + (all ? "logout-all" : "logout"), {
      method: "POST",
    });
    epoch.current++;
    setUser(null);
    setSaved(new Set());
  }
  async function toggle(item: NewsItem) {
    if (!user) throw new Error("请先登录");
    const version = epoch.current,
      removing = saved.has(item.id);
    await request(
      `/bookmarks/${item.id}`,
      removing
        ? { method: "DELETE" }
        : {
            method: "PUT",
            body: JSON.stringify({ report_date: item.report_date }),
          },
    );
    if (version === epoch.current)
      setSaved((previous) => {
        const next = new Set(previous);
        if (removing) next.delete(item.id);
        else next.add(item.id);
        return next;
      });
  }
  return (
    <Context.Provider value={{ user, loading, saved, refresh, logout, toggle }}>
      {children}
    </Context.Provider>
  );
}
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider missing");
  return value;
}
