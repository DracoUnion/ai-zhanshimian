// 与后端 schema 对齐的类型（见 doc/design-detail.md 第三章）

export interface ApiEnvelope<T> {
  code: number;
  message: string;
  data: T;
}

export interface User {
  id: number;
  phone: string;
  nickname: string | null;
  avatar_url: string | null;
  unlocked: boolean;
  credits: number;
  trial_used: boolean;
  trial_available: boolean;
}

export interface TokenResult {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}

export interface Template {
  id: number;
  name: string;
  category: string;
  cover_url: string | null;
  prompt_template: string;
  prompt_tips: string | null;
  sort: number;
}

export type GenerationStatus = 'pending' | 'processing' | 'success' | 'failed';

export interface ImageItem {
  url: string;
  width: number;
  height: number;
}

export interface GenerationTemplate {
  id: number;
  name: string;
  cover_url: string | null;
}

export interface GenerationDetail {
  generation_id: number;
  status: GenerationStatus;
  quantity: number;
  credit_cost: number;
  charged: boolean;
  selfie_url: string | null;
  reference_url: string | null;
  prompt: string | null;
  template: GenerationTemplate | null;
  results: ImageItem[];
  fail_reason: string | null;
  created_at: string | null;
  finished_at: string | null;
}

export interface GenerationCreateResult {
  generation_id: number;
  status: string;
  quantity: number;
  credit_cost: number;
  trial_used: boolean;
  balance: number;
}

export interface GenerationListItem {
  generation_id: number;
  status: GenerationStatus;
  quantity: number;
  credit_cost: number;
  template_name: string | null;
  first_result_url: string | null;
  created_at: string | null;
}

export interface GenerationListOut {
  items: GenerationListItem[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface UploadTarget {
  object_key: string;
  upload_url: string;
  view_url: string;
  expires_in: number;
  method: 'PUT';
  headers: Record<string, string>;
}

export interface CreatePaymentResult {
  order_no: string;
  status: string;
  pay_params: Record<string, unknown>;
}

export interface OrderResult {
  order_no: string;
  order_type: 'unlock' | 'recharge';
  status: 'pending' | 'paid' | 'closed' | 'refunded';
  amount: number;
  credits: number;
  created_at: string | null;
  paid_at: string | null;
}

export interface HealthResult {
  status: string;
  env: string;
  payment_mode: string;
}