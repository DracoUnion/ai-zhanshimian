import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useGenerations } from '../api/hooks';
import { fmtTime } from '../utils/format';

const STATUS_TEXT: Record<string, string> = {
  pending: '排队中',
  processing: '生成中',
  success: '完成',
  failed: '失败',
};

export default function HistoryPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const { data, isLoading } = useGenerations(page);

  if (!user) {
    return (
      <div className="empty">
        <p className="empty-big">登录后查看生成记录</p>
        <Link className="btn btn--gold" to="/workspace">
          去生成
        </Link>
      </div>
    );
  }

  const items = data?.items ?? [];

  return (
    <div className="history">
      <div className="section-title">我的生成记录</div>
      {isLoading && !items.length ? (
        <p className="muted">加载中…</p>
      ) : items.length === 0 ? (
        <div className="empty">
          <p className="muted">还没有生成记录</p>
          <Link className="btn btn--ghost" to="/workspace">
            去生成第一张
          </Link>
        </div>
      ) : (
        <>
          <div className="history-list">
            {items.map((it) => (
              <Link className={`history-item is-${it.status}`} key={it.generation_id} to={`/result/${it.generation_id}`}>
                {it.first_result_url ? (
                  <img src={it.first_result_url} alt="" loading="lazy" />
                ) : (
                  <div className="his-ph">{STATUS_TEXT[it.status] ?? it.status}</div>
                )}
                <div className="his-info">
                  <b>{it.template_name ?? '自定义提示词'}</b>
                  <span className="muted">
                    {fmtTime(it.created_at)} · {it.quantity} 张
                    {it.credit_cost > 0 ? ` · 扣 ${it.credit_cost} 次` : ''}
                  </span>
                </div>
                <span className={`badge badge--${it.status}`}>{STATUS_TEXT[it.status] ?? it.status}</span>
              </Link>
            ))}
          </div>
          {data && data.has_more && (
            <button className="btn btn--ghost btn--block" onClick={() => setPage((p) => p + 1)}>
              加载更多
            </button>
          )}
        </>
      )}
    </div>
  );
}