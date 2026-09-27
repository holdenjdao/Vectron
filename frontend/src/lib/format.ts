// Formatting helpers for timestamps, durations, sizes and counts.

const pad = (value: number, width = 2): string => String(value).padStart(width, "0");

/**
 * Parses an API timestamp (ISO 8601 as emitted by pydantic, e.g.
 * "2026-09-27T21:04:17.123456Z") into epoch milliseconds. Extra fractional
 * digits are trimmed for engines that only accept milliseconds, and a missing
 * zone is read as UTC.
 */
export function parseTime(value: string | null | undefined): number | null {
  if (!value) return null;
  let iso = value.trim().replace(/(\.\d{3})\d+/, "$1");
  if (/T\d{2}:\d{2}/.test(iso) && !/(?:Z|[+-]\d{2}:?\d{2})$/i.test(iso)) iso += "Z";
  const ms = Date.parse(iso);
  return Number.isNaN(ms) ? null : ms;
}

/** Local wall-clock time with milliseconds: `HH:MM:SS.mmm`. */
export function formatClock(ms: number): string {
  const d = new Date(ms);
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}.${pad(d.getMilliseconds(), 3)}`;
}

/** Local date and time: `YYYY-MM-DD HH:MM`. */
export function formatDateTime(ms: number): string {
  const d = new Date(ms);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** Full timestamp for tooltips. */
export function formatTooltipTime(ms: number): string {
  return new Date(ms).toString();
}

/** Compact relative time: "just now", "42s ago", "5m ago", "3h ago", "4d ago", then a date. */
export function formatRelative(ms: number, now: number): string {
  const seconds = Math.max(0, now - ms) / 1000;
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${Math.floor(seconds)}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 7 * 86_400) return `${Math.floor(seconds / 86_400)}d ago`;
  return formatDateTime(ms).slice(0, 10);
}

/** Task durations: "0.42s", "12.4s", "3m 07s", "1h 02m". */
export function formatDuration(ms: number): string {
  const safe = Number.isFinite(ms) && ms > 0 ? ms : 0;
  const seconds = safe / 1000;
  if (seconds < 10) return `${seconds.toFixed(2)}s`;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const whole = Math.floor(seconds);
  const h = Math.floor(whole / 3600);
  const m = Math.floor((whole % 3600) / 60);
  return h > 0 ? `${h}h ${pad(m)}m` : `${m}m ${pad(whole % 60)}s`;
}

/** Stopwatch style elapsed time: "00:07.3", "12:41.0", "1:02:03". */
export function formatElapsed(ms: number): string {
  const safe = Number.isFinite(ms) && ms > 0 ? ms : 0;
  const tenths = Math.floor(safe / 100);
  const totalSeconds = Math.floor(tenths / 10);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}:${pad(m)}:${pad(s)}`;
  return `${pad(m)}:${pad(s)}.${tenths % 10}`;
}

/** File sizes: "812 B", "84.2 KB", "1.4 MB". */
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes < 1024) return `${Math.round(bytes)} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value < 100 ? value.toFixed(1) : Math.round(value)} ${units[unit]}`;
}

const trimZero = (text: string): string => text.replace(/\.0$/, "");

/** Compact counts: 842, "12.4K", "3.1M". */
export function formatCompact(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  if (abs < 1000) return String(Math.round(value));
  if (abs < 1_000_000) return `${trimZero((value / 1000).toFixed(1))}K`;
  if (abs < 1_000_000_000) return `${trimZero((value / 1_000_000).toFixed(1))}M`;
  return `${trimZero((value / 1_000_000_000).toFixed(1))}B`;
}

export function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

export function basename(path: string): string {
  const index = path.lastIndexOf("/");
  return index >= 0 ? path.slice(index + 1) : path;
}

export function extension(path: string): string {
  const name = basename(path);
  const index = name.lastIndexOf(".");
  return index > 0 ? name.slice(index + 1).toLowerCase() : "";
}
