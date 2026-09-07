import { useTemplates } from '../api/hooks';

interface Props {
  value: number | null;
  onPick: (id: number) => void;
}

const PALETTE = ['#2b2a45', '#223a34', '#381f2d', '#2e3a25', '#332e1d'];

export default function TemplatePicker({ value, onPick }: Props) {
  const { data, isLoading } = useTemplates();
  const items = data?.items ?? [];

  return (
    <section className="block">
      <div className="section-title">
        选择风格
        <span className="muted">先选氛围，再看提示词</span>
      </div>
      {isLoading ? (
        <div className="muted">加载模板中…</div>
      ) : (
        <div className="template-grid">
          {items.map((t, i) => (
            <button
              key={t.id}
              type="button"
              className={`tpl-card ${value === t.id ? 'is-active' : ''}`}
              style={{ ['--tpl' as string]: PALETTE[i % PALETTE.length] }}
              onClick={() => onPick(t.id)}
            >
              {t.cover_url ? <img src={t.cover_url} alt={t.name} /> : <div className="tpl-cover">{t.name.slice(0, 1)}</div>}
              <b>{t.name}</b>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}