import type { ReactNode } from 'react';
import { Link, NavLink } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useModal } from '../modal/ModalContext';

const tabs = [
  { to: '/', label: '首页', end: true },
  { to: '/workspace', label: '生成' },
  { to: '/history', label: '记录' },
  { to: '/account', label: '我的' },
];

export default function Layout({ children }: { children: ReactNode }) {
  const { user, booting } = useAuth();
  const { showLogin } = useModal();

  return (
    <div className="app">
      <header className="topbar">
        <Link to="/" className="brand">
          <span className="brand-mark">✦</span>
          <span className="brand-name">AI 展示面大师</span>
        </Link>
        <div className="topbar-right">
          {user ? (
            <>
              <Link to="/pricing" className="chip chip--gold" title="可用次数">
                <b>{user.credits}</b>
                <span> 次</span>
              </Link>
            </>
          ) : (
            <button className="chip chip--cta" onClick={() => showLogin()}>
              登录
            </button>
          )}
        </div>
      </header>

      <main className="main">
        {booting ? <div className="full-loader" /> : children}
      </main>

      <nav className="tabbar">
        {tabs.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end} className={({ isActive }) => (isActive ? 'is-active' : '')}>
            {t.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}