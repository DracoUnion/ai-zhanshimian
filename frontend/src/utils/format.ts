// 展示/格式化工具

export function maskPhone(phone: string): string {
  return phone.length === 11 ? phone.replace(/^(\d{3})\d{4}(\d{4})$/, '$1****$2') : phone;
}

export function fenToYuan(fen: number): string {
  return (fen / 100).toFixed(fen % 100 === 0 ? 0 : 2);
}

export function fmtTime(iso: string | null): string {
  if (!iso) return '-';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '-';
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getMonth() + 1}/${d.getDate()} ${p(d.getHours())}:${p(d.getMinutes())}`;
}