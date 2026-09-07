import { request } from './client';
import type { TokenResult } from '../types';

export const authApi = {
  sendCode: (phone: string) =>
    request<{ cooldown: number }>({ url: '/api/v1/auth/sms-code', method: 'POST', data: { phone } }),
  // 仅开发/mock：读取验证码用于本地联调
  devCode: (phone: string) =>
    request<{ code: string | null }>({ url: '/api/v1/auth/dev-code', method: 'POST', data: { phone } }),
  phoneLogin: (phone: string, code: string) =>
    request<TokenResult>({ url: '/api/v1/auth/phone-login', method: 'POST', data: { phone, code } }),
};