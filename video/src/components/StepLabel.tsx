import { useCurrentFrame } from "remotion";

import { inOut, progress } from "../lib/anim";
import { colors, fonts, type } from "../theme";

interface Props {
  step: string;
  label: string;
  start: number;
  exit?: number;
  tag?: string;
}

/** "01 — DESCRIBE": the small mono label that names each step. */
export const StepLabel: React.FC<Props> = ({ step, label, start, exit, tag }) => {
  const frame = useCurrentFrame();
  const o = inOut(frame, start, exit);
  const rule = progress(frame, start + 4, 18);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 18,
        fontFamily: fonts.mono,
        fontWeight: 500,
        fontSize: type.label,
        letterSpacing: "0.16em",
        textTransform: "uppercase",
        opacity: o,
        transform: `translateY(${(1 - o) * 12}px)`,
      }}
    >
      <span style={{ color: colors.accent }}>{step}</span>
      <span style={{ width: 48 * rule, height: 2, background: colors.accent, opacity: 0.8 }} />
      <span style={{ color: colors.text }}>{label}</span>
      {tag ? (
        <span
          style={{
            marginLeft: 6,
            padding: "6px 12px",
            border: `1px solid ${colors.line}`,
            borderRadius: 999,
            color: colors.dim,
            fontSize: type.micro,
            letterSpacing: "0.14em",
          }}
        >
          {tag}
        </span>
      ) : null}
    </div>
  );
};
