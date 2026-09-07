// 全局弹窗（登录 / 支付）：由 App 统一挂载，任何页面可唤起
import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import LoginModal from '../components/LoginModal';
import PayModal from '../components/PayModal';

export interface PaySpec {
  orderType: 'unlock' | 'recharge';
  /** recharge 时的套餐金额（分），缺省 5000 */
  amount?: number;
  onPaid?: () => void;
}

interface ModalCtx {
  showLogin: (done?: () => void) => void;
  showPay: (spec: PaySpec) => void;
}

const Ctx = createContext<ModalCtx | null>(null);

export function ModalProvider({ children }: { children: ReactNode }) {
  const [loginOpen, setLoginOpen] = useState(false);
  const [loginDone, setLoginDone] = useState<(() => void) | null>(null);
  const [paySpec, setPaySpec] = useState<PaySpec | null>(null);

  const showLogin = useCallback((done?: () => void) => {
    setLoginDone(done ?? null);
    setLoginOpen(true);
  }, []);

  const showPay = useCallback((spec: PaySpec) => setPaySpec(spec), []);

  const value = useMemo<ModalCtx>(() => ({ showLogin, showPay }), [showLogin, showPay]);

  return (
    <Ctx.Provider value={value}>
      {children}
      <LoginModal
        open={loginOpen}
        onClose={() => {
          setLoginOpen(false);
          setLoginDone(null);
        }}
        onSuccess={() => {
          const done = loginDone;
          setLoginOpen(false);
          setLoginDone(null);
          done?.();
        }}
      />
      {paySpec && <PayModal spec={paySpec} onClose={() => setPaySpec(null)} />}
    </Ctx.Provider>
  );
}

export function useModal(): ModalCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useModal 必须在 ModalProvider 内使用');
  return v;
}