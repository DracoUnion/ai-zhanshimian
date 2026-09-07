export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner-wrap">
      <div className="spinner" aria-hidden="true" />
      {label && <p className="spinner-label">{label}</p>}
    </div>
  );
}

/** 整页加载态 */
export function FullLoader({ label }: { label?: string }) {
  return (
    <div className="full-loader">
      <Spinner label={label} />
    </div>
  );
}