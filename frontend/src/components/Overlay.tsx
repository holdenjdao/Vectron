import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { cx } from "../lib/cx";

interface Props {
  title: string;
  onClose: () => void;
  /** Extra header controls (e.g. a download link). */
  actions?: ReactNode;
  bodyClassName?: string;
  children: ReactNode;
}

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Full-screen modal viewer. Esc or a click on the backdrop closes it; focus is
 * trapped inside while open and returned to the opener afterwards.
 */
export function Overlay({ title, onClose, actions, bodyClassName, children }: Props) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();

    const onKey = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      opener?.focus();
    };
  }, []);

  // Keep Tab / Shift+Tab cycling inside the dialog.
  const trapFocus = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab" || !dialogRef.current) return;
    const nodes = Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
    const first = nodes[0];
    const last = nodes[nodes.length - 1];
    if (!first || !last) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return createPortal(
    <div
      className="overlay"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        className="overlay__dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={trapFocus}
      >
        <header className="overlay__head">
          <h2 className="overlay__title" id={titleId}>
            {title}
          </h2>
          <div className="overlay__actions">
            {actions}
            <button
              ref={closeRef}
              type="button"
              className="icon-button"
              onClick={onClose}
              aria-label="Close full-screen view"
              title="Close (Esc)"
            >
              ✕
            </button>
          </div>
        </header>
        <div className={cx("overlay__body", bodyClassName)}>{children}</div>
      </div>
    </div>,
    document.body,
  );
}
