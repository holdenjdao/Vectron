import { cx } from "../lib/cx";

interface Props {
  text: string | undefined;
  position?: "top" | "bottom";
}

/** Classification marking strip (top and bottom of every page). */
export function ClassificationBanner({ text, position = "top" }: Props) {
  const marking = text?.trim() || "UNCLASSIFIED";
  return (
    <div
      className={cx("banner", position === "bottom" && "banner--bottom")}
      role="note"
      aria-label={`Classification: ${marking}`}
    >
      {marking}
    </div>
  );
}
