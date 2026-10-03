import type { ReactNode } from "react";

import { cx } from "../lib/cx";
import { Glyph } from "./Status";

interface Props {
  tone?: "danger" | "warn" | "info";
  title?: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}

/** Inline message box for errors and notices. Danger callouts are announced to screen readers. */
export function Callout({ tone = "danger", title, children, actions, className }: Props) {
  return (
    <div
      className={cx("callout", `callout--${tone}`, className)}
      role={tone === "danger" ? "alert" : "status"}
    >
      <span className={cx("status-icon", `tone-${tone}`)}>
        <Glyph kind={tone === "danger" ? "cross" : "alert"} />
      </span>
      <div className="callout__body">
        {title && <strong className="callout__title">{title}</strong>}
        <div className="callout__text">{children}</div>
        {actions && <div className="callout__actions">{actions}</div>}
      </div>
    </div>
  );
}
