// 轻量全局消息提示（无第三方依赖）
import { createContext, useCallback, useContext, useRef, useState } from 'react';
import type { ReactNode } from 'react';

type ToastKind = 'info' | 'success' | 'error';
interface ToastItem {
  id: number;
  text: string;
  kind: ToastKind;
}

type Push = (text: string, kind?: ToastKind) => void;

const ToastCtx = createContext<Push>(() => undefined);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const seq = useRef(0);

  const push = useCallback<Push>((text, kind = 'info') => {
    const id = ++seq.current;
    setItems((s) => [...s.slice(-2), { id, text, kind }]);
    setTimeout(() => setItems((s) => s.filter((x) => x.id !== id)), 2600);
  }, []);

  return (
    <ToastCtx.Provider value={push}>
      <div className="toasts" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast toast--${t.kind}`}>
            {t.text}
          </div>
        ))}
      </div>
      {children}
    </ToastCtx.Provider>
  );
}

export function useToast(): Push {
  return useContext(ToastCtx);
}