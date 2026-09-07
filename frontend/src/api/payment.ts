import { request } from './client';
import type { CreatePaymentResult, OrderResult } from '../types';

export const paymentApi = {
  create: (body: { amount: number; order_type: 'unlock' | 'recharge'; pay_type: 'h5' | 'native' }) =>
    request<CreatePaymentResult>({ url: '/api/v1/payments/recharge', method: 'POST', data: body }),
  mockConfirm: (order_no: string) =>
    request<{ order_no: string; status: string }>({
      url: '/api/v1/payments/mock-confirm',
      method: 'POST',
      data: { order_no },
    }),
  order: (order_no: string) => request<OrderResult>({ url: `/api/v1/payments/orders/${order_no}` }),
};