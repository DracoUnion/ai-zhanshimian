import { useQuery } from '@tanstack/react-query';
import { generationApi } from './generation';
import { paymentApi } from './payment';
import { templateApi } from './template';

export const QK = {
  templates: ['templates'] as const,
  generation: (id: number) => ['generation', id] as const,
  order: (orderNo: string) => ['order', orderNo] as const,
  generations: (page: number) => ['generations', page] as const,
};

/** 生成详情：pending/processing 时每 2s 轮询，终态自动停止 */
export function usePollGeneration(id: number) {
  return useQuery({
    queryKey: QK.generation(id),
    queryFn: () => generationApi.detail(id),
    refetchInterval: (query) =>
      query.state.data?.status === 'pending' || query.state.data?.status === 'processing' ? 2000 : false,
  });
}

/** 订单状态：pending 时每 2s 轮询 */
export function usePollOrder(orderNo: string | null) {
  return useQuery({
    queryKey: QK.order(orderNo ?? ''),
    queryFn: () => paymentApi.order(orderNo as string),
    enabled: !!orderNo,
    refetchInterval: (query) => (query.state.data?.status === 'pending' ? 2000 : false),
  });
}

export function useTemplates() {
  return useQuery({ queryKey: QK.templates, queryFn: templateApi.list, staleTime: Infinity });
}

export function useGenerations(page = 1) {
  return useQuery({ queryKey: QK.generations(page), queryFn: () => generationApi.list(page) });
}