import { useCurrentFrame } from "remotion";

import { easeIn, kf, progress } from "../lib/anim";
import { colors, fonts } from "../theme";

interface Props {
  lines: string[];
  /** Frame (local to the parent sequence) the first line starts. */
  start: number;
  /** Frames between lines. */
  stagger?: number;
  /** Frame the block finishes leaving; omit to stay. */
  exit?: number;
  size: number;
  weight?: number;
  /** Colour per line; defaults to white. */
  lineColors?: string[];
  lineHeight?: number;
  letterSpacing?: string;
  align?: "left" | "center";
}

/** Headline lines that slide up out of a mask, one after another, in reading order. */
export const RevealLines: React.FC<Props> = ({
  lines,
  start,
  stagger = 8,
  exit,
  size,
  weight = 700,
  lineColors,
  lineHeight = 1.08,
  letterSpacing = "-0.035em",
  align = "left",
}) => {
  const frame = useCurrentFrame();
  const out = exit === undefined ? 0 : kf(frame, [exit - 14, exit], [0, 1], easeIn);
  return (
    <div style={{ textAlign: align }}>
      {lines.map((line, i) => {
        const p = progress(frame, start + i * stagger, 22);
        return (
          <div key={i} style={{ overflow: "hidden", paddingBottom: size * 0.12, marginBottom: -size * 0.12 }}>
            <div
              style={{
                fontFamily: fonts.sans,
                fontWeight: weight,
                fontSize: size,
                lineHeight,
                letterSpacing,
                color: lineColors?.[i] ?? colors.text,
                transform: `translateY(${(1 - p) * 105 + out * -40}%)`,
                opacity: (0.2 + 0.8 * p) * (1 - out),
                whiteSpace: "nowrap",
              }}
            >
              {line}
            </div>
          </div>
        );
      })}
    </div>
  );
};
