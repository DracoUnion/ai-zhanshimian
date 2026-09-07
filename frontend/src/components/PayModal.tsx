import { useState } from 'react';
import { paymentApi } from '../api/payment';
import { useAuth } from '../auth/AuthContext';
import { useToast } from '../toast';
import { fenToYuan } from '../utils/format';
import type { PaySpec } from '../modal/ModalContext';

interface Props {
  spec: PaySpec;
  onClose: () => void;
}

const MAX_POLL = 30;

export default function PayModal({ spec, onClose }: Props) {
  const { refreshUser } = useAuth();
  const toast = useToast();

  const [orderNo, setOrderNo] = useState<string | null>(null);
  const [payParams, setPayParams] = useState<Record<string, unknown> | null>(null);
  const [creating, setCreating] = useState(false);
  const [paid, setPaid] = useState(false);

  const isUnlock = spec.orderType === 'unlock';
  const amount = isUnlock ? 6900 : spec.amount ?? 5000;
  const price = fenToYuan(amount);
  const isMock = !!payParams?.mock;

  const done = async () => {
    setPaid(true);
    await refreshUser();
    toast('支付成功', 'success');
    spec.onPaid?.();
    // 稍等片刻再关闭，展示余额更新
    setTimeout(onClose, 700);
  };

  const createOrder = async () => {
    setCreating(true);
    try {
      const r = await paymentApi.create({ amount, order_type: spec.orderType, pay_type: 'h5' });
      setOrderNo(r.order_no);
      setPayParams(r.pay_params);
    } catch (e) {
      toast((e as Error).message || '下单失败', 'error');
    }
    setCreating(false);
  };

  // mock 模式：直接模拟微信到账
  const mockConfirm = async () => {
    if (!orderNo) return;
    try {
      await paymentApi.mockConfirm(orderNo);
      await done();
    } catch (e) {
      toast((e as Error).message || '结算失败', 'error');
    }
  };

  // 真实微信模式：拉起收银台并轮询订单
  const payWechatAndPoll = async () => {
    if (!payParams) return;
    const h5 = payParams.h5_url as string | undefined;
    if (h5) {
      window.location.href = h5;
    }
    for (let i = 0; i < MAX_POLL; i++) {
      await new Promise((r) => setTimeout(r, 2000));
      const o = await paymentApi.order(orderNo as string).catch(() => null);
      if (o?.status === 'paid') {
        await done();
        return;
      }
    }
    toast('等待支付超时，请稍后到「我的」查看', 'info');
  };

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{isUnlock ? '69 元解锁全部功能' : '余额充值'}</h3>
        <div className="price-disp">
          <span className="price-big">¥{price}</span>
          {!isUnlock && <span className="muted">到账 {amount / 100} 次（约 1 元/次）</span>}
        </div>

        {!orderNo && (
          <button className="btn btn--gold btn--block" disabled={creating} onClick={createOrder}>
            {creating ? '创建订单中…' : `确认支付 ¥${price}`}
          </button>
        )}

        {orderNo && isMock && (
          <button className="btn btn--gold btn--block" onClick={mockConfirm}>
            模拟到账（开发联调用）
          </button>
        )}

        {orderNo && !isMock && (
          <>
            {payParams?.code_url ? (
              <p className="muted">请使用微信扫一扫完成支付（PC 场景）</p>
            ) : (
              <p className="muted">请在微信支付页面完成付款，本页将自动检测</p>
            )}
            <button className="btn btn--ghost btn--block" onClick={payWechatAndPoll}>
              前往微信支付
            </button>
            <p className="muted small">订单号：{orderNo}</p>
          </>
        )}

        <button className="text-link" onClick={onClose}>
          {paid ? '关闭' : '取消'}
        </button>
      </div>
    </div>
  );
}