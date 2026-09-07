import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useModal } from '../modal/ModalContext';
import { userApi } from '../api/user';
import { maskPhone } from '../utils/format';
import { useToast } from '../toast';

export default function AccountPage() {
  const { user, logout, refreshUser } = useAuth();
  const { showLogin, showPay } = useModal();
  const toast = useToast();
  const [name, setName] = useState(user?.nickname ?? '');
  const [saving, setSaving] = useState(false);

  if (!user) {
    return (
      <div className="empty">
        <p className="empty-big">登录后查看我的展示面</p>
        <button className="btn btn--gold" onClick={() => showLogin()}>
          手机号登录
        </button>
      </div>
    );
  }

  const saveName = async () => {
    setSaving(true);
    try {
      await userApi.update({ nickname: name.trim() || null });
      await refreshUser();
      toast('已保存', 'success');
    } catch (e) {
      toast((e as Error).message || '保存失败', 'error');
    }
    setSaving(false);
  };

  return (
    <div className="account">
      <section className="balance-card">
        <div className="balance-row">
          <div>
            <p className="muted">可用生成次数</p>
            <p className="balance-num">{user.credits}</p>
          </div>
          <button className="btn btn--gold" onClick={() => showPay({ orderType: 'recharge', amount: 5000 })}>
            充值
          </button>
        </div>
        <div className="status-row">
          <span className={user.unlocked ? 'st st--ok' : 'st'}>解锁：{user.unlocked ? '已解锁 69 包' : '未解锁'}</span>
          <span className="st">试用：{user.trial_used ? '已用' : '未用（可用 1 次）'}</span>
        </div>
      </section>

      <section className="block">
        <div className="section-title">资料</div>
        <input
          className="field"
          placeholder="昵称（用于个人简介建议）"
          value={name}
          maxLength={16}
          onChange={(e) => setName(e.target.value)}
        />
        <button className="btn btn--ghost btn--block" disabled={saving} onClick={() => void saveName()}>
          {saving ? '保存中…' : '保存'}
        </button>
        <p className="muted note">手机号：{maskPhone(user.phone)}</p>
      </section>

      <section className="block">
        <div className="section-title">更多</div>
        <Link className="list-row" to="/history">
          <span>生成记录</span>
          <span className="muted">›</span>
        </Link>
        <Link className="list-row" to="/pricing">
          <span>套餐与充值</span>
          <span className="muted">›</span>
        </Link>
        <button className="list-row list-row--btn" onClick={logout}>
          <span>退出登录</span>
        </button>
      </section>
    </div>
  );
}