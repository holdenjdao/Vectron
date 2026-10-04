import { AbsoluteFill, useCurrentFrame } from "remotion";

import { RevealLines } from "../components/RevealLines";
import { StepLabel } from "../components/StepLabel";
import { VectronMark } from "../components/VectronMark";
import { copy, integrations } from "../content";
import { easeIn, inOut, kf, progress } from "../lib/anim";
import { colors, fonts, type } from "../theme";
import { durations } from "../timing";
import { HUB } from "./Deliver";

export const HUB_TILE = 200;
export const HUB_MARK = 96;

const ROW_GAP = 78;
const LEFT_EDGE = 700; // right edge of the left chips
const RIGHT_EDGE = 1220; // left edge of the right chips

const rowY = (i: number, n: number) => HUB.y + (i - (n - 1) / 2) * ROW_GAP;

/** 5 · Integrate: the build becomes a hub that connects to the rest of the toolchain. */
export const Integrate: React.FC = () => {
  const frame = useCurrentFrame();
  const end = durations.integrate;
  const c = copy.integrate;
  const hubIn = progress(frame, 0, 20);
  const retract = kf(frame, [end - 22, end - 4], [0, 1], easeIn);
  const tileFade = kf(frame, [end - 16, end], [1, 0]);

  const side = (group: typeof integrations.left, dir: -1 | 1) =>
    group.items.map((name, i) => {
      const y = rowY(i, group.items.length);
      const start = 14 + i * 4 + (dir === 1 ? 2 : 0);
      const draw = progress(frame, start, 22) * (1 - retract);
      const chip = inOut(frame, start + 12, undefined, 14) * (1 - retract);
      const hubX = HUB.x + dir * (HUB_TILE / 2);
      const edge = dir === -1 ? LEFT_EDGE : RIGHT_EDGE;
      const mid = (hubX + edge) / 2;
      return {
        name,
        y,
        chip,
        path: `M ${hubX} ${HUB.y} C ${mid} ${HUB.y}, ${mid} ${y}, ${edge} ${y}`,
        draw,
        edge,
      };
    });

  const left = side(integrations.left, -1);
  const right = side(integrations.right, 1);
  const titleY = rowY(0, 5) - 72;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: 120, width: "100%", display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
        <StepLabel step={c.step} label={c.label} tag={c.tag || undefined} start={4} exit={end - 8} />
        <RevealLines lines={c.headline} start={10} exit={end - 8} size={type.headline} align="center" />
      </div>

      <svg width={1920} height={1080} style={{ position: "absolute", inset: 0 }}>
        {[...left, ...right].map((l) => (
          <g key={l.name}>
            <path d={l.path} fill="none" stroke="rgba(255,255,255,0.22)" strokeWidth={1.5} pathLength={1} strokeDasharray={1} strokeDashoffset={1 - l.draw} />
            <circle cx={l.edge} cy={l.y} r={4} fill={colors.accent} opacity={l.chip} />
          </g>
        ))}
      </svg>

      {[
        { title: integrations.left.title, x: LEFT_EDGE, align: "right" as const, rows: left },
        { title: integrations.right.title, x: RIGHT_EDGE, align: "left" as const, rows: right },
      ].map((col) => (
        <div key={col.title}>
          <div
            style={{
              position: "absolute",
              top: titleY,
              ...(col.align === "right" ? { right: 1920 - col.x } : { left: col.x }),
              fontFamily: fonts.mono,
              fontWeight: 500,
              fontSize: type.micro,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: colors.dim,
              opacity: inOut(frame, 16, end - 10),
            }}
          >
            {col.title}
          </div>
          {col.rows.map((row) => (
            <div
              key={row.name}
              style={{
                position: "absolute",
                top: row.y - 28,
                ...(col.align === "right" ? { right: 1920 - col.x + 14 } : { left: col.x + 14 }),
                height: 56,
                padding: "0 28px",
                display: "flex",
                alignItems: "center",
                borderRadius: 999,
                border: `1px solid ${colors.line}`,
                background: "rgba(255,255,255,0.035)",
                fontFamily: fonts.sans,
                fontWeight: 600,
                fontSize: 26,
                color: colors.text,
                whiteSpace: "nowrap",
                opacity: row.chip,
                transform: `translateX(${(1 - row.chip) * (col.align === "right" ? 24 : -24)}px)`,
              }}
            >
              {row.name}
            </div>
          ))}
        </div>
      ))}

      {/* The hub: the folded build. Its mark hands over to the closing scene. */}
      <div
        style={{
          position: "absolute",
          left: HUB.x - HUB_TILE / 2,
          top: HUB.y - HUB_TILE / 2,
          width: HUB_TILE,
          height: HUB_TILE,
          borderRadius: 32,
          background: colors.bgRaised,
          border: "1px solid rgba(255,255,255,0.12)",
          boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 80px rgba(179,38,12,${0.35 * hubIn})`,
          opacity: hubIn * tileFade,
          transform: `scale(${0.6 + 0.4 * hubIn})`,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: HUB.x - HUB_MARK / 2,
          top: HUB.y - HUB_MARK / 2 - 4,
          opacity: hubIn,
          transform: `scale(${0.6 + 0.4 * hubIn})`,
        }}
      >
        <VectronMark size={HUB_MARK} />
      </div>
      <div
        style={{
          position: "absolute",
          top: HUB.y + HUB_TILE / 2 + 22,
          width: "100%",
          textAlign: "center",
          fontFamily: fonts.mono,
          fontWeight: 500,
          fontSize: type.micro,
          letterSpacing: "0.16em",
          textTransform: "uppercase",
          color: colors.dim,
          opacity: inOut(frame, 10, end - 10),
        }}
      >
        {c.hub}
      </div>
    </AbsoluteFill>
  );
};
