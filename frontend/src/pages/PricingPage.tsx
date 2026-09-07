import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useModal } from '../modal/ModalContext';

const PACKAGES = [5000, 10000, 20000];

export default function PricingPage() {
  const { user } = useAuth();
  const { showLogin, showPay } = useModal();

  const buy = (spec: { orderType: 'unlock' | 'recharge'; amount?: number }) => {
    if (!user) {
      showLogin(() => buy(spec));
      return;
    }
    showPay(spec);
  };

  return (
    <div className="pricing">
      <section className="unlock-card">
        <span className="tag tag--gold">最多人购买</span>
        <h2>69 元解锁全部功能</h2>
        <ul className="feat-list">
          <li>免费体验 1 张之后，无限继续生成</li>
          <li>赠送 69 次生成额度（1 元/次）</li>
          <li>全部风格模板 + 多张成组</li>
          <li>生成失败自动退回次数</li>
        </ul>
        <button
          className="btn btn--gold btn--block"
          disabled={user?.unlocked}
          onClick={() => buy({ orderType: 'unlock' })}
        >
          {user?.unlocked ? '已解锁 ✓' : user ? '¥69 立即解锁' : '登录后解锁'}
        </button>
      </section>

      <section className="block">
        <div className="section-title">
          按需充值
          <span className="muted">不买断也能用，充多少生成多少次</span>
        </div>
        <div className="recharge-grid">
          {PACKAGES.map((amount) => (
            <button key={amount} className="recharge-card" onClick={() => buy({ orderType: 'recharge', amount })}>
              <b>¥{amount / 100}</b>
              <span className="muted">到账 {amount / 100} 次</span>
            </button>
          ))}
        </div>
        <p className="muted note">约 1 元/次；成功生成才扣费，失败自动退回。</p>
      </section>

      <p className="muted center">
        高客单用户想全托管代运营？<Link to="/account" style={{ color: 'var(--accent)' }}>联系我们</Link>
      </p>
    </div>
  );
}