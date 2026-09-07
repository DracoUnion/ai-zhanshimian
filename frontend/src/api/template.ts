import { request } from './client';
import type { Template } from '../types';

export const templateApi = {
  list: () => request<{ items: Template[] }>({ url: '/api/v1/templates' }),
};