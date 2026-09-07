// axios 客户端：统一响应包裹解包 + JWT 注入 + 401 自动刷新重试 + 登出广播
import axios, { AxiosError, AxiosRequestConfig } from 'axios';
import type { ApiEnvelope } from '../types';

export const ACCESS_KEY = 'zs_access';
export const REFRESH_KEY = 'zs_refresh';

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  setTokens(access_token: string, refresh_token: string) {
    localStorage.setItem(ACCESS_KEY, access_token);
    localStorage.setItem(REFRESH_KEY, refresh_token);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  code: number;
  constructor(code: number, message: string) {
    super(message);
    this.code = code;
  }
}

type ReqConfig = AxiosRequestConfig & { skipAuth?: boolean; _retried?: boolean };

export type { ReqConfig };

export const raw = axios.create({ baseURL: '', timeout: 20000 });

raw.interceptors.request.use((config) => {
  const c = config as ReqConfig;
  const access = tokenStore.access;
  if (access && !c.skipAuth) {
    (config.headers as Record<string, string>)['Authorization'] = `Bearer ${access}`;
  }
  return config;
});

let refreshing: Promise<boolean> | null = null;

async function refreshToken(): Promise<boolean> {
  const rt = tokenStore.refresh;
  if (!rt) return false;
  try {
    const resp = await axios.post<ApiEnvelope<{ access_token: string; expires_in: number }>>(
      '/api/v1/auth/refresh',
      { refresh_token: rt },
    );
    const env = resp.data;
    if (env.code === 0) {
      localStorage.setItem(ACCESS_KEY, env.data.access_token);
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

export function emitAuthLogout() {
  window.dispatchEvent(new CustomEvent('auth:logout'));
}

export async function request<T>(cfg: ReqConfig): Promise<T> {
  try {
    const resp = await raw.request<ApiEnvelope<T>>(cfg);
    const env = resp.data;
    if (env && env.code === 0) {
      return env.data;
    }
    throw new ApiError(env?.code ?? -1, env?.message ?? '请求失败');
  } catch (err) {
    const ax = err as AxiosError;
    if (ax.isAxiosError && ax.response?.status === 401 && !cfg._retried) {
      refreshing = refreshing ?? refreshToken();
      const ok = await refreshing;
      refreshing = null;
      if (ok) {
        cfg._retried = true;
        return request<T>(cfg);
      }
      tokenStore.clear();
      emitAuthLogout();
      throw new ApiError(1001, '登录已过期，请重新登录');
    }
    if (err instanceof ApiError) throw err;
    if (axios.isAxiosError(err)) {
      const env = err.response?.data as Partial<ApiEnvelope<unknown>> | undefined;
      if (env?.code) throw new ApiError(env.code, env.message || '请求失败');
      throw new ApiError(-1, '网络连接异常');
    }
    throw new ApiError(-1, String(err));
  }
}