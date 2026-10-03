// Status indicators. Every state has a distinct shape as well as a colour, and a text label.

import type { CheckStatus, JobStatus, TaskStatus } from "../api/types";
import { cx } from "../lib/cx";
import { JOB_STATUS_LABEL, TASK_STATUS_LABEL } from "../lib/status";

type GlyphKind = "hollow" | "pulse" | "check" | "cross" | "dash" | "alert";

/** 14px status glyph drawn in `currentColor`. */
export function Glyph({ kind, size = 14 }: { kind: GlyphKind; size?: number }) {
  return (
    <svg
      className="glyph"
      width={size}
      height={size}
      viewBox="0 0 14 14"
      aria-hidden="true"
      focusable="false"
    >
      {kind === "hollow" && (
        <circle cx="7" cy="7" r="4.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      )}
      {kind === "pulse" && (
        <>
          <circle className="glyph__pulse" cx="7" cy="7" r="3.5" fill="currentColor" opacity="0.5" />
          <circle cx="7" cy="7" r="3.5" fill="currentColor" />
        </>
      )}
      {kind === "check" && (
        <path
          d="M2.8 7.3 L5.8 10.2 L11.2 4.1"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.9"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}
      {kind === "cross" && (
        <path
          d="M3.6 3.6 L10.4 10.4 M10.4 3.6 L3.6 10.4"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.9"
          strokeLinecap="round"
        />
      )}
      {kind === "dash" && (
        <path d="M3.4 7 H10.6" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
      )}
      {kind === "alert" && (
        <>
          <path
            d="M7 1.8 L12.6 11.6 H1.4 Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinejoin="round"
          />
          <path d="M7 5.6 V8.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="7" cy="10" r="0.8" fill="currentColor" />
        </>
      )}
    </svg>
  );
}

const TASK_GLYPH: Record<TaskStatus, GlyphKind> = {
  pending: "hollow",
  running: "pulse",
  succeeded: "check",
  failed: "cross",
  skipped: "dash",
};

/** Task status icon with a screen-reader label. */
export function TaskStatusIcon({ status }: { status: TaskStatus }) {
  const label = TASK_STATUS_LABEL[status] ?? status;
  return (
    <span className={cx("status-icon", `tone-${status}`)} title={label}>
      <Glyph kind={TASK_GLYPH[status] ?? "hollow"} />
      <span className="sr-only">{label}</span>
    </span>
  );
}

const JOB_GLYPH: Record<JobStatus, GlyphKind> = {
  queued: "hollow",
  running: "pulse",
  succeeded: "check",
  failed: "cross",
};

const JOB_CHIP_TONE: Record<JobStatus, string | null> = {
  queued: null,
  running: "chip--accent",
  succeeded: "chip--accent",
  failed: "chip--danger",
};

/** Job status as a labelled chip. */
export function JobStatusChip({ status, small = false }: { status: JobStatus; small?: boolean }) {
  return (
    <span className={cx("chip", JOB_CHIP_TONE[status], small && "chip--sm")}>
      <Glyph kind={JOB_GLYPH[status] ?? "hollow"} size={small ? 12 : 14} />
      {JOB_STATUS_LABEL[status] ?? status}
    </span>
  );
}

const CHECK_GLYPH: Record<CheckStatus, GlyphKind> = { pass: "check", warn: "alert", fail: "cross" };

export function CheckStatusIcon({ status }: { status: CheckStatus }) {
  return (
    <span className={cx("status-icon", `tone-${status}`)}>
      <Glyph kind={CHECK_GLYPH[status] ?? "hollow"} />
    </span>
  );
}
