import type { JobProgress } from "../api/types";
import { cx } from "../lib/cx";
import { doneCount } from "../lib/status";

interface Props {
  progress: JobProgress;
  size?: "sm" | "md";
  label?: string;
}

/** Segmented task progress: succeeded, failed, skipped, then running (striped). */
export function ProgressBar({ progress, size = "md", label = "Task progress" }: Props) {
  const { total, succeeded, failed, skipped, running } = progress;
  const done = doneCount(progress);
  const pct = (n: number) => `${total > 0 ? Math.min(100, (n / total) * 100) : 0}%`;
  return (
    <div
      className={cx("progress", `progress--${size}`)}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={Math.max(total, 1)}
      aria-valuenow={done}
      aria-valuetext={`${done} of ${total} tasks finished${failed ? `, ${failed} failed` : ""}`}
    >
      <span className="progress__seg progress__seg--ok" style={{ width: pct(succeeded) }} />
      <span className="progress__seg progress__seg--fail" style={{ width: pct(failed) }} />
      <span className="progress__seg progress__seg--skip" style={{ width: pct(skipped) }} />
      <span className="progress__seg progress__seg--run" style={{ width: pct(running) }} />
    </div>
  );
}
