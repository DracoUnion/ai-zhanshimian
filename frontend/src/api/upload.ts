import { raw, request } from './client';
import type { ReqConfig } from './client';
import type { UploadTarget } from '../types';

export const uploadApi = {
  presign: (kind: 'selfie' | 'reference', content_type: string, size: number) =>
    request<UploadTarget>({
      url: '/api/v1/uploads/presign',
      method: 'POST',
      data: { kind, content_type, size },
    }),
  signview: (object_keys: string[]) =>
    request<{ urls: Record<string, string> }>({
      url: '/api/v1/uploads/signview',
      method: 'POST',
      data: { object_keys },
    }),
};

export async function uploadRaw(target: UploadTarget, blob: Blob): Promise<void> {
  const crossOrigin =
    target.upload_url.startsWith('http') && !target.upload_url.startsWith(window.location.origin);
  const cfg: ReqConfig = {
    url: target.upload_url,
    method: 'PUT',
    data: blob,
    headers: { 'Content-Type': blob.type || 'image/jpeg' },
    skipAuth: crossOrigin, // 跨域预签名（S3）不能带 Bearer；同源本地接口需要
    timeout: 60000,
  };
  await raw.request<Blob>(cfg);
}