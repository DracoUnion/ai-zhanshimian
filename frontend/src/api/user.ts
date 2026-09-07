import { request } from './client';
import type { User } from '../types';

export const userApi = {
  me: () => request<User>({ url: '/api/v1/users/me' }),
  update: (patch: { nickname?: string | null; avatar_url?: string | null }) =>
    request<User>({ url: '/api/v1/users/me', method: 'PATCH', data: patch }),
};