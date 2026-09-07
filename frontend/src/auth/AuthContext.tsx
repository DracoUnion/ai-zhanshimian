import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { authApi } from '../api/auth';
import { userApi } from '../api/user';
import { tokenStore } from '../api/client';
import type { User } from '../types';

interface AuthCtx {
  user: User | null;
  booting: boolean;
  login: (phone: string, code: string) => Promise<User>;
  logout: () => void;
  /** 支付/解锁等余额变动后刷新当前用户 */
  refreshUser: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let alive = true;
    const boot = async () => {
      if (!tokenStore.access) {
        setBooting(false);
        return;
      }
      try {
        const u = await userApi.me();
        if (alive) setUser(u);
      } catch {
        tokenStore.clear();
      }
      if (alive) setBooting(false);
    };
    boot();
    const onLogout = () => setUser(null);
    window.addEventListener('auth:logout', onLogout);
    return () => {
      alive = false;
      window.removeEventListener('auth:logout', onLogout);
    };
  }, []);

  const login = useCallback(async (phone: string, code: string) => {
    const t = await authApi.phoneLogin(phone, code);
    tokenStore.setTokens(t.access_token, t.refresh_token);
    setUser(t.user);
    return t.user;
  }, []);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!tokenStore.access) return;
    try {
      setUser(await userApi.me());
    } catch {
      /* 保持原状态，后续请求兜底 */
    }
  }, []);

  const value = useMemo<AuthCtx>(
    () => ({ user, booting, login, logout, refreshUser }),
    [user, booting, login, logout, refreshUser],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth 必须在 AuthProvider 内使用');
  return v;
}