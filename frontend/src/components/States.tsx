import type { ReactNode } from "react";

import { cx } from "../lib/cx";

/** Spinner with an uppercase status line, announced politely. */
export function Loading({ text = "Loading…", compact = false }: { text?: string; compact?: boolean }) {
  return (
    <div className={cx("placeholder", compact && "placeholder--compact")} role="status">
      <span className="inline-loading">
        <span className="spinner" aria-hidden="true" />
        {text}
      </span>
    </div>
  );
}

/** Placeholder for sections without content yet. */
export function EmptyState({
  text,
  hint,
  compact = false,
  children,
}: {
  text: string;
  hint?: ReactNode;
  compact?: boolean;
  children?: ReactNode;
}) {
  return (
    <div className={cx("placeholder", compact && "placeholder--compact")}>
      <p className="placeholder__text">{text}</p>
      {hint && <p className="placeholder__hint">{hint}</p>}
      {children}
    </div>
  );
}
