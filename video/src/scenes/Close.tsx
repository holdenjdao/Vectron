import { AbsoluteFill, useCurrentFrame } from "remotion";

import { RevealLines } from "../components/RevealLines";
import { VectronMark } from "../components/VectronMark";
import { copy } from "../content";
import { easeInOut, inOut, kf, progress } from "../lib/anim";
import { colors, fonts, type } from "../theme";
import { HUB } from "./Deliver";
import { HUB_MARK } from "./Integrate";

const MARK = { x: 960, y: 340, size: 132 };

/** 6 · Close: the hub's mark rises, the tagline lands, the frame holds. */
export const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const move = progress(frame, 0, 28, easeInOut);
  const size = kf(move, [0, 1], [HUB_MARK, MARK.size], (t) => t);
  const x = kf(move, [0, 1], [HUB.x, MARK.x], (t) => t);
  const y = kf(move, [0, 1], [HUB.y - 4, MARK.y], (t) => t);
  const rule = progress(frame, 40, 22);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: x - size / 2, top: y - size / 2 }}>
        <VectronMark size={size} />
      </div>
      <div style={{ position: "absolute", top: 470, width: "100%" }}>
        <RevealLines
          lines={copy.close.tagline}
          start={16}
          stagger={10}
          size={84}
          align="center"
          lineColors={[colors.text, colors.accent]}
          letterSpacing="-0.04em"
        />
      </div>
      <div
        style={{
          position: "absolute",
          top: 730,
          width: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 26,
        }}
      >
        <span style={{ width: 120 * rule, height: 2, background: colors.accent, opacity: 0.8 }} />
        <span
          style={{
            fontFamily: fonts.mono,
            fontWeight: 500,
            fontSize: type.label,
            letterSpacing: "0.22em",
            textTransform: "uppercase",
            color: colors.dim,
            opacity: inOut(frame, 46),
          }}
        >
          <span style={{ color: colors.text, textTransform: "none" }}>{copy.brand}</span>
          {"  ·  "}
          {copy.close.footer}
        </span>
      </div>
    </AbsoluteFill>
  );
};
