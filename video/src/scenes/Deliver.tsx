import { AbsoluteFill, useCurrentFrame } from "remotion";

import { Card } from "../components/Card";
import { RevealLines } from "../components/RevealLines";
import { StepLabel } from "../components/StepLabel";
import { assets, copy } from "../content";
import { easeIn, inOut, kf, progress } from "../lib/anim";
import { colors, fonts, type } from "../theme";
import { durations } from "../timing";

/** Where the cards fold to at the end: the hub of the next scene. */
export const HUB = { x: 960, y: 600 };

const CARDS = [
  { key: "code", src: assets.code, natural: { width: 1648, height: 1398 }, left: 110, top: 120, width: 560, at: 12, labelAt: "top" },
  { key: "diagram", src: assets.diagram, natural: { width: 1588, height: 1164 }, left: 430, top: 300, width: 720, at: 18, labelAt: "top" },
  { key: "inspection", src: assets.inspection, natural: { width: 1648, height: 1020 }, left: 150, top: 640, width: 540, at: 24, labelAt: "bottom" },
] as const;

/** 4 · Deliver: the outputs come forward as layered cards; copy on the right. */
export const Deliver: React.FC = () => {
  const frame = useCurrentFrame();
  const end = durations.deliver;
  const c = copy.deliver;
  const fold = kf(frame, [end - 24, end], [0, 1], easeIn);
  const drift = kf(frame, [0, end], [0, 1], (t) => t);
  return (
    <AbsoluteFill>
      {CARDS.map((card) => {
        const p = progress(frame, card.at, 26);
        const height = (card.width * card.natural.height) / card.natural.width;
        const cx = card.left + card.width / 2;
        const cy = card.top + height / 2;
        // Settle in from below, drift a touch, then fold toward the hub.
        const dx = (HUB.x - cx) * fold;
        const dy = (1 - p) * 90 + (HUB.y - cy) * fold - drift * 10;
        const s = (0.92 + 0.08 * p + drift * 0.02) * (1 - fold * 0.85);
        return (
          <div
            key={card.key}
            style={{
              position: "absolute",
              inset: 0,
              opacity: p * (1 - fold),
              transform: `translate(${dx}px, ${dy}px)`,
            }}
          >
            <div style={{ position: "absolute", inset: 0, transform: `scale(${s})`, transformOrigin: `${cx}px ${cy}px` }}>
              <Card
                src={card.src}
                natural={card.natural}
                width={card.width}
                label={c.cards[card.key]}
                labelAt={card.labelAt}
                style={{ left: card.left, top: card.top }}
              />
            </div>
          </div>
        );
      })}

      <div style={{ position: "absolute", left: 1260, top: 300 }}>
        <StepLabel step={c.step} label={c.label} start={16} exit={end - 6} />
      </div>
      <div style={{ position: "absolute", left: 1260, top: 356 }}>
        <RevealLines
          lines={c.headline}
          start={22}
          stagger={7}
          exit={end - 6}
          size={type.headline}
          lineColors={[colors.text, colors.text, colors.accent]}
        />
      </div>
      <div style={{ position: "absolute", left: 1260, top: 618, width: 520 }}>
        {c.stats.map((stat, i) => (
          <div
            key={stat}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 14,
              padding: "12px 0",
              borderTop: `1px solid ${colors.line}`,
              fontFamily: fonts.mono,
              fontWeight: 500,
              fontSize: type.label,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: colors.text,
              opacity: inOut(frame, 44 + i * 5, end - 6, 14),
            }}
          >
            <span style={{ width: 8, height: 8, borderRadius: 4, background: colors.accent }} />
            {stat}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
