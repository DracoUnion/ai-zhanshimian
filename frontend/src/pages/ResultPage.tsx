import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { usePollGeneration } from '../api/hooks';
import { FullLoader, Spinner } from '../components/Spinner';
import ResultGallery from '../components/ResultGallery';

export default function ResultPage() {
  const { id } = useParams();
  const genId = Number(id);
  const { user } = useAuth();
  const { data: g, isLoading, isError } = usePollGeneration(Number.isFinite(genId) ? genId : NaN);

  if (isLoading && !g) return <FullLoader label="加载生成结果…" />;
  if (isError || !g) {
    return (
      <div className="empty">
        <p>找不到这条生成记录</p>
        <Link className="btn btn--ghost" to="/workspace">
          返回生成
        </Link>
      </div>
    );
  }

  const generating = g.status === 'pending' || g.status === 'processing';
  const isTrialFree = g.credit_cost === 0;
  const showUnlockHint = isTrialFree && user && !user.unlocked;

  return (
    <div className="result-page">
      {generating ? (
        <div className="generation-loading">
          <Spinner label="AI 正在为你生成…" />
          <p className="muted">约 30 秒~2 分钟，生成失败会自动退回次数，请稍候</p>
        </div>
      ) : g.status === 'success' ? (
        <>
          {showUnlockHint && (
            <div className="unlock-hint">
              <div>
                <b>这张是免费体验</b>
                <p className="muted">解锁后继续生成，风格模板 + 多张成组全开放</p>
              </div>
              <Link className="btn btn--gold" to="/pricing">
                去解锁
              </Link>
            </div>
          )}
          <ResultGallery shots={g.results} title={`已生成 ${g.results.length} 张`} />
          <div className="btn-row">
            <Link className="btn btn--ghost" to="/workspace">
              再生成一组
            </Link>
            <Link className="btn btn--gold" to={user ? '/history' : '/pricing'}>
              {user ? '查看我的记录' : '解锁更多'}
            </Link>
          </div>
        </>
      ) : (
        <div className="empty">
          <p className="empty-big">生成未成功</p>
          <p className="muted">{g.fail_reason || '未知错误'}</p>
          <p className="muted">已为你退回本次次数</p>
          <Link className="btn btn--gold" to="/workspace">
            重新生成
          </Link>
        </div>
      )}
    </div>
  );
}