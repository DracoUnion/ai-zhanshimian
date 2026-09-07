import { request } from './client';
import type { GenerationCreateResult, GenerationDetail, GenerationListOut } from '../types';

export interface GenerationCreateBody {
  selfie_key: string;
  reference_key?: string | null;
  template_id?: number | null;
  prompt?: string | null;
  quantity: number;
}

export const generationApi = {
  create: (body: GenerationCreateBody, idempotencyKey: string) =>
    request<GenerationCreateResult>({
      url: '/api/v1/generations',
      method: 'POST',
      data: body,
      headers: { 'Idempotency-Key': idempotencyKey },
    }),
  detail: (id: number) => request<GenerationDetail>({ url: `/api/v1/generations/${id}` }),
  list: (page = 1, pageSize = 20) =>
    request<GenerationListOut>({ url: '/api/v1/generations', params: { page, page_size: pageSize } }),
  remove: (id: number) => request<null>({ url: `/api/v1/generations/${id}`, method: 'DELETE' }),
};