import { useEffect, useState } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authApi } from '../api/auth';
import { useToast } from '../toast';

interface Props {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export default function LoginModal({ open, onClose, onSuccess }: Props) {
  const { login } = useAuth();
  const toast = useToast();

  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) {
      setPhone('');
      setCode('');
      setCountdown(0);
    }
  }, [open]);

  useEffect(() => {
    if (countdown <= 0) return;
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [countdown]);

  const sendCode = async () => {
    if (!/^1[3-9]\d{9}$/.test(phone)) {
      toast('请输入正确的手机号', 'error');
      return;
    }
    setSending(true);
    try {
      await authApi.sendCode(phone);
      setCountdown(60);
      // 开发/mock：自动填入验证码，便于本地联调
      try {
        const d = await authApi.devCode(phone);
        if (d.code) setCode(d.code);
      } catch {
        /* 生产环境无 dev-code 接口，忽略 */
      }
      toast('验证码已发送');
    } catch (e) {
      toast((e as Error).message || '发送失败', 'error');
    }
    setSending(false);
  };

  const submit = async () => {
    if (code.trim().length < 4) {
      toast('请输入验证码', 'error');
      return;
    }
    setLoading(true);
    try {
      await login(phone.trim(), code.trim());
      toast('登录成功', 'success');
      onSuccess();
    } catch (e) {
      toast((e as Error).message || '登录失败', 'error');
    }
    setLoading(false);
  };

  if (!open) return null;

  return (
    <div className="modal-mask" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>手机号登录</h3>
        <p className="muted">新用户自动注册，并获赠 1 次免费体验</p>
        <input
          className="field"
          placeholder="手机号"
          inputMode="numeric"
          maxLength={11}
          value={phone}
          onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))}
        />
        <div className="row">
          <input
            className="field"
            placeholder="验证码"
            inputMode="numeric"
            maxLength={6}
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          />
          <button className="btn btn--ghost btn--nowrap" disabled={countdown > 0 || sending} onClick={sendCode}>
            {countdown > 0 ? `${countdown}s 后重发` : sending ? '发送中…' : '获取验证码'}
          </button>
        </div>
        <button className="btn btn--gold btn--block" disabled={loading} onClick={submit}>
          {loading ? '登录中…' : '登录 / 注册'}
        </button>
        <button className="text-link" onClick={onClose}>
          暂不登录
        </button>
      </div>
    </div>
  );
}