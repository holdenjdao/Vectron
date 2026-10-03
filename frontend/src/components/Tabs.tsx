import { useRef, type KeyboardEvent } from "react";

import { cx } from "../lib/cx";

export interface TabItem<T extends string> {
  id: T;
  label: string;
  count?: number | null;
  /** Colours the count badge (e.g. failed inspection checks). */
  tone?: "danger" | "warn" | null;
}

interface Props<T extends string> {
  label: string;
  idBase: string;
  items: TabItem<T>[];
  active: T;
  onChange: (id: T) => void;
}

export const tabId = (base: string, id: string) => `${base}-tab-${id}`;
export const tabPanelId = (base: string, id: string) => `${base}-panel-${id}`;

/** WAI-ARIA tabs: arrow keys / Home / End move between tabs (automatic activation). */
export function Tabs<T extends string>({ label, idBase, items, active, onChange }: Props<T>) {
  const buttons = useRef(new Map<T, HTMLButtonElement>());

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = items.length - 1;
    const target =
      event.key === "ArrowRight" ? (index === last ? 0 : index + 1)
      : event.key === "ArrowLeft" ? (index === 0 ? last : index - 1)
      : event.key === "Home" ? 0
      : event.key === "End" ? last
      : -1;
    const item = items[target];
    if (!item) return;
    event.preventDefault();
    onChange(item.id);
    buttons.current.get(item.id)?.focus();
  };

  return (
    <div className="tabs" role="tablist" aria-label={label}>
      {items.map((item, index) => {
        const selected = item.id === active;
        return (
          <button
            key={item.id}
            ref={(el) => {
              if (el) buttons.current.set(item.id, el);
              else buttons.current.delete(item.id);
            }}
            type="button"
            role="tab"
            id={tabId(idBase, item.id)}
            aria-selected={selected}
            aria-controls={tabPanelId(idBase, item.id)}
            tabIndex={selected ? 0 : -1}
            className="tab"
            onClick={() => onChange(item.id)}
            onKeyDown={(event) => onKeyDown(event, index)}
          >
            {item.label}
            {item.count != null && (
              <span className={cx("tab__count", item.tone && `tab__count--${item.tone}`)}>
                {item.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
