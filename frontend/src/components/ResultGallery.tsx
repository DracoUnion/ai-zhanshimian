interface Shot {
  url: string;
}

interface Props {
  shots: Shot[];
  title?: string;
}

export default function ResultGallery({ shots, title }: Props) {
  if (!shots.length) return null;
  return (
    <section className="block">
      {title && <div className="section-title">{title}</div>}
      <div className="gallery">
        {shots.map((s, i) => (
          <figure key={i} className={`shot ${shots.length === 1 ? 'shot--single' : ''}`}>
            <img src={s.url} alt={`生成结果 ${i + 1}`} loading="lazy" />
            <a className="shot-dl" href={s.url} download={`展示面-${i + 1}.jpg`}>
              保存
            </a>
          </figure>
        ))}
      </div>
    </section>
  );
}