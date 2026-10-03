import { useId, type ReactNode } from "react";

import { cx } from "../lib/cx";

interface Props {
  title: ReactNode;
  /** Right-aligned header content (counts, links, stream state…). */
  meta?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** A titled console section. */
export function Panel({ title, meta, className, children }: Props) {
  const titleId = useId();
  return (
    <section className={cx("panel", className)} aria-labelledby={titleId}>
      <header className="panel__head">
        <h2 className="panel__title" id={titleId}>
          {title}
        </h2>
        {meta != null && <div className="panel__meta">{meta}</div>}
      </header>
      {children}
    </section>
  );
}
