import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { auth } from "../api/endpoints";
import { setUnauthorizedHandler, tokenStore } from "../api/client";
import type { RegisterIn, User } from "../api/types";

interface AuthCtx {
  user: User | null;
  ready: boolean;                      // đã kiểm tra token cũ xong chưa (tránh nháy về trang đăng nhập)
  login: (email: string, password: string, remember: boolean) => Promise<void>;
  register: (data: RegisterIn) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);               // token hết hạn ở bất kỳ request nào → về trang đăng nhập
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    auth.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setReady(true));
  }, [logout]);

  const login = useCallback(async (email: string, password: string, remember: boolean) => {
    const { access_token } = await auth.login(email, password);
    tokenStore.set(access_token, remember);
    setUser(await auth.me());
  }, []);

  const register = useCallback(async (data: RegisterIn) => {
    await auth.register(data);
    await login(data.email, data.password, false);
  }, [login]);

  const value = useMemo(() => ({ user, ready, login, register, logout }), [user, ready, login, register, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth phải nằm trong <AuthProvider>");
  return ctx;
}
