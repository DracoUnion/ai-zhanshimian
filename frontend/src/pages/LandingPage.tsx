import { Link } from 'react-router-dom';

const STEPS = [
  { n: '01', t: '上传一张正面自拍', d: '不改变五官，只优化穿搭、光线与场景' },
  { n: '02', t: '选择喜欢的风格', d: '海边、咖啡厅、健身房… 10+ 氛围可选' },
  { n: '03', t: 'AI 生成展示面', d: '约 1 元/张，成功后才扣次数' },
];

export default function LandingPage() {
  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-badge">先免费生成 1 张</div>
        <h1 className="hero-title">
          普通男生，也能有
          <br />
          让人<em>多看一眼</em>的照片
        </h1>
        <p className="hero-sub">
          手机相册全是工作截图？让 AI 帮你把一张自拍，变成自带氛围感的社交展示面。
        </p>
        <Link className="btn btn--gold btn--lg" to="/workspace">
          免费生成一张 →
        </Link>
        <div className="hero-notes">
          <span>✓ 无需会拍照</span>
          <span>✓ 无需懂 AI</span>
          <span>✓ 手机就能用</span>
        </div>
      </section>

      <section className="block howto">
        <div className="section-title">三步获得展示面</div>
        <ol className="steps">
          {STEPS.map((s) => (
            <li key={s.n}>
              <b>{s.n}</b>
              <div>
                <p className="step-t">{s.t}</p>
                <p className="muted">{s.d}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="block pricing-teaser">
        <div className="section-title">定价简单</div>
        <div className="teaser-card">
          <span className="teaser-free">先体验 · 再付费</span>
          <p className="teaser-price">
            ¥<b>69</b> 解锁全部功能
          </p>
          <p className="muted">约 1 元/张 · 用完按需充值 · 失败自动退回</p>
          <Link className="btn btn--ghost" to="/pricing">
            查看套餐
          </Link>
        </div>
      </section>
    </div>
  );
}