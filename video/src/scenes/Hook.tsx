import { AbsoluteFill, useCurrentFrame } from "remotion";

import { RevealLines } from "../components/RevealLines";
import { VectronMark } from "../components/VectronMark";
import { copy } from "../content";
import { inOut, progress } from "../lib/anim";
import { colors, fonts, type } from "../theme";
import { durations } from "../timing";

/** 1 · Hook: the promise in two lines, before any UI. */
export const Hook: React.FC = () => {
  const frame = useCurrentFrame();
  const end = durations.hook;
  const label = inOut(frame, 2, end - 4);
  const lift = progress(frame, end - 18, 18);
  return (
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
      <div
        style={{
          position: "absolute",
          top: 120,
          display: "flex",
          alignItems: "center",
          gap: 14,
          opacity: label,
          fontFamily: fonts.mono,
          fontWeight: 500,
          fontSize: type.label,
          letterSpacing: "0.22em",
          textTransform: "uppercase",
          color: colors.dim,
        }}
      >
        <VectronMark size={34} draw={progress(frame, 2, 26)} />
        {copy.brandLabel}
      </div>
      <div style={{ transform: `translateY(${-lift * 60}px)` }}>
        <RevealLines
          lines={copy.hook}
          start={8}
          stagger={16}
          exit={end}
          size={type.hook}
          lineColors={[colors.text, colors.accent]}
          align="center"
          letterSpacing="-0.045em"
        />
      </div>
    </AbsoluteFill>
  );
};
