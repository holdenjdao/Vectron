import { AbsoluteFill, useCurrentFrame } from "remotion";

import { RevealLines } from "../components/RevealLines";
import { StepLabel } from "../components/StepLabel";
import { copy } from "../content";
import { inOut, kf, progress } from "../lib/anim";
import { buildPosition } from "../lib/buildClock";
import { colors, fonts, type } from "../theme";
import { durations } from "../timing";

/** 3 · Build: the crew list lights up in step with the build on screen. */
export const BuildCopy: React.FC = () => {
  const frame = useCurrentFrame();
  const end = durations.build;
  const c = copy.build;
  const pos = buildPosition(frame);
  const out = kf(frame, [end - 16, end], [1, 0]);
  return (
    <AbsoluteFill style={{ opacity: out }}>
      <div style={{ position: "absolute", left: 120, top: 196 }}>
        <StepLabel step={c.step} label={c.label} start={4} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 256 }}>
        <RevealLines lines={c.headline} start={10} stagger={7} size={type.headline} />
      </div>
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 410,
          width: 520,
          fontFamily: fonts.sans,
          fontSize: 28,
          lineHeight: 1.4,
          color: colors.dim,
          opacity: inOut(frame, 24),
        }}
      >
        {c.sub}
      </div>
      <div style={{ position: "absolute", left: 120, top: 500, display: "grid", gap: 14 }}>
        {c.roles.map((role, i) => {
          const shown = inOut(frame, 28 + i * 3, undefined, 12);
          const lit = progress(pos, role.at - 0.5, 0.5, (t) => t);
          return (
            <div
              key={role.name}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 16,
                height: 32,
                opacity: shown,
                transform: `translateX(${(1 - shown) * -16}px)`,
              }}
            >
              <svg width={22} height={22} viewBox="0 0 22 22">
                <circle cx={11} cy={11} r={9.5} fill="none" stroke={colors.faint} strokeWidth={1.5} opacity={1 - lit} />
                <circle cx={11} cy={11} r={10} fill={colors.accent} opacity={lit} />
                <path
                  d="M6.5 11.3 L9.6 14.2 L15.5 8"
                  fill="none"
                  stroke={colors.bg}
                  strokeWidth={2.2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  opacity={lit}
                />
              </svg>
              <span
                style={{
                  fontFamily: fonts.mono,
                  fontWeight: 500,
                  fontSize: type.label,
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                  color: lit > 0.5 ? colors.text : colors.faint,
                  minWidth: 250,
                }}
              >
                {role.name}
              </span>
              <span style={{ fontFamily: fonts.sans, fontSize: type.micro, color: colors.dim, opacity: 0.35 + lit * 0.65 }}>
                {role.detail}
              </span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
