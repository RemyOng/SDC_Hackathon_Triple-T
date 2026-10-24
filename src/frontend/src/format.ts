const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** 2026-11-10 -> 10 Nov 2026 */
export function date(value: string): string {
  const [y, m, d] = value.slice(0, 10).split("-").map(Number);
  return `${d} ${months[m - 1]} ${y}`;
}

/** ISO timestamp -> 24 Oct 2026, 13:20 */
export function dateTime(value: string): string {
  return `${date(value)}, ${value.slice(11, 16)}`;
}

export function time(value: string): string {
  return value.slice(11, 16);
}

/** 2140 -> RM2,140 · -203.31 -> −RM203.31 */
export function rm(value: number, decimals = 0): string {
  const text = Math.abs(value).toLocaleString("en-MY", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
  return `${value < 0 ? "−" : ""}RM${text}`;
}

export function num(value: number, decimals = 0): string {
  return value.toLocaleString("en-MY", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function years(value: number | null): string {
  if (value === null) return "—";
  return `${num(value, value % 1 ? 1 : 0)} ${value === 1 ? "year" : "years"}`;
}
