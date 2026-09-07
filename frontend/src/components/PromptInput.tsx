const PRESETS = ['日系', '商务', '运动', '文艺', '都市'];

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export default function PromptInput({ value, onChange, placeholder }: Props) {
  return (
    <section className="block">
      <div className="section-title">
        提示词
        <span className="muted">越具体越接近你想要的氛围</span>
      </div>
      <div className="prompt-chips">
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            className="chip-chip"
            onClick={() => {
              if (value) onChange(`${value}，${p}风格`);
              else onChange(`${p}风格，自然不做作`);
            }}
          >
            {p}
          </button>
        ))}
      </div>
      <textarea
        className="field field--area"
        placeholder={placeholder ?? '补充穿搭、光线、场景细节…'}
        value={value}
        maxLength={120}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="count">
        <span className="muted">{value.length}/120</span>
      </div>
    </section>
  );
}