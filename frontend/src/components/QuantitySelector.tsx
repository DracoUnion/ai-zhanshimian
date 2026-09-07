const OPTIONS = [
  { n: 1, note: '约 1 元' },
  { n: 6, note: '多张更划算' },
  { n: 12, note: '成系列出图' },
];

interface Props {
  value: number;
  onChange: (n: number) => void;
}

export default function QuantitySelector({ value, onChange }: Props) {
  return (
    <section className="block">
      <div className="section-title">
        生成张数
        <span className="muted">每次生成会在成功后才扣次数</span>
      </div>
      <div className="qty-row">
        {OPTIONS.map((o) => (
          <button key={o.n} type="button" className={`qty ${value === o.n ? 'is-active' : ''}`} onClick={() => onChange(o.n)}>
            <b>{o.n} 张</b>
            <i>{o.note}</i>
          </button>
        ))}
      </div>
    </section>
  );
}