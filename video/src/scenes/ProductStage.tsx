import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

import { BrowserFrame, CHROME_HEIGHT } from "../components/BrowserFrame";
import { assets, ui } from "../content";
import { ease, easeIn, easeInOut, inOut, kf, progress } from "../lib/anim";
import { BUILD_STATES, buildPosition } from "../lib/buildClock";
import { colors } from "../theme";
import { durations } from "../timing";

const D = durations.describe;
const B = durations.build;

/** Browser page width at camera zoom 1. */
const PAGE_WIDTH = 1296;
const PAGE_SCALE = PAGE_WIDTH / ui.viewport.width;

/**
 * A camera shot: put app point `focus` (CSS px) at frame point `at`, at `zoom`.
 * Returns the browser's top-left and scale in frame px.
 */
const shot = (focus: [number, number], at: [number, number], zoom: number) => ({
  x: at[0] - zoom * PAGE_SCALE * focus[0],
  y: at[1] - zoom * (CHROME_HEIGHT + PAGE_SCALE * focus[1]),
  z: zoom,
});

const center = (r: { x: number; y: number; width: number; height: number }): [number, number] => [
  r.x + r.width / 2,
  r.y + r.height / 2,
];

// The camera path through Describe → Build → the start of Deliver (frames local to this stage).
const SHOTS = [
  { f: 0, ...shot([720, 450], [960, 640], 0.96) }, // rising in
  { f: 24, ...shot([720, 450], [960, 600], 1) }, // full product view
  { f: 36, ...shot([720, 450], [960, 600], 1) },
  { f: 62, ...shot(center(ui.briefPanel), [960, 620], 1.6) }, // close on the brief
  { f: D - 14, ...shot(center(ui.briefPanel), [960, 620], 1.6) },
  { f: D + 18, x: 700, y: 161, z: 0.887 }, // split: browser right, copy left
  { f: D + 62, x: 700, y: 161, z: 0.887 },
  { f: D + 98, ...shot([420, 420], [1240, 560], 1.3) }, // closer on the assembly line
  { f: D + B, ...shot([420, 420], [1240, 560], 1.3) },
  { f: D + B + 24, ...shot([720, 450], [960, 560], 0.8) }, // recedes behind the cards
];

const cam = (frame: number, key: "x" | "y" | "z") =>
  interpolate(
    frame,
    SHOTS.map((s) => s.f),
    SHOTS.map((s) => s[key]),
    { easing: easeInOut, extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );

const pad = (n: number) => String(n).padStart(3, "0");

const Full: React.FC<{ src: string; opacity?: number }> = ({ src, opacity = 1 }) => (
  <Img
    src={staticFile(src)}
    style={{ position: "absolute", inset: 0, width: ui.viewport.width, height: ui.viewport.height, opacity }}
  />
);

const box = (r: { x: number; y: number; width: number; height: number }, grow = 0): React.CSSProperties => ({
  position: "absolute",
  left: r.x - grow,
  top: r.y - grow,
  width: r.width + grow * 2,
  height: r.height + grow * 2,
});

export const ProductStage: React.FC = () => {
  const f = useCurrentFrame();

  const x = cam(f, "x");
  const y = cam(f, "y");
  const z = cam(f, "z");
  const enter = progress(f, 0, 24);
  const recede = progress(f, D + B, 24, easeInOut);
  const leave = kf(f, [D + B + 4, D + B + 22], [0, 1], easeIn);

  // Describe: type the brief, then press Build.
  const TYPE = [64, 104];
  const typed = Math.round(kf(f, TYPE, [0, assets.briefFrames - 1], (t) => t));
  const briefOn = f >= TYPE[0];
  const spotlight = inOut(f, 40, D - 2, 18);
  const PRESS = 112;
  const cursorIn = progress(f, 100, 12);
  const pressed = f >= PRESS && f < PRESS + 5;
  const ring = kf(f, [PRESS, PRESS + 14], [0, 1]);
  const ringFade = kf(f, [PRESS + 6, PRESS + 22], [1, 0]);

  // Build: the captured job page, frame by frame with a short dissolve.
  const toBuild = kf(f, [D - 6, D + 2], [0, 1], ease);
  const pos = buildPosition(f - D);
  const i = Math.floor(pos);
  const mix = kf(pos - i, [0.65, 1], [0, 1], (t) => t);
  const buildSrc = (n: number) => (n >= BUILD_STATES - 1 ? assets.jobDone : `ui/build/${pad(n)}.jpg`);
  const statusRing = inOut(f, D + 110, D + B + 6, 14);

  // Cursor travels from the end of the typed brief to the Build button.
  const btn = center(ui.buildButton);
  const cx = interpolate(cursorIn, [0, 1], [700, btn[0] - 40]);
  const cy = interpolate(cursorIn, [0, 1], [318, btn[1] + 2]);

  return (
    <AbsoluteFill style={{ opacity: enter * (1 - leave) }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          transform: `translate(${x}px, ${y}px) scale(${z})`,
          transformOrigin: "0 0",
          filter: `blur(${recede * 6}px) brightness(${1 - recede * 0.55})`,
        }}
      >
        <BrowserFrame width={PAGE_WIDTH} url={toBuild < 0.5 ? "localhost:8000/app/" : "localhost:8000/app/#/jobs"}>
          <Full src={assets.catalog} />
          <Full src={assets.catalogWithBrief} opacity={kf(f, [TYPE[1], TYPE[1] + 6], [0, 1])} />
          {briefOn ? (
            <Img src={staticFile(`ui/brief/${pad(typed)}.jpg`)} style={box(ui.briefPanel)} />
          ) : null}

          {/* Dim everything but the brief. */}
          <div
            style={{
              ...box(ui.briefPanel, 6),
              borderRadius: 8,
              boxShadow: `0 0 0 3000px rgba(6, 7, 10, ${0.62 * spotlight})`,
            }}
          />

          {/* Press feedback on Build from brief. */}
          <div style={{ ...box(ui.buildButton), background: pressed ? "rgba(0,0,0,0.28)" : "transparent" }} />
          <div
            style={{
              ...box(ui.buildButton, 4 + (1 - ring) * 10),
              border: `2px solid ${colors.accent}`,
              borderRadius: 6,
              opacity: ring > 0 ? ringFade : 0,
              boxShadow: `0 0 24px rgba(246,128,32,0.45)`,
            }}
          />
          <svg
            width={24}
            height={24}
            viewBox="0 0 24 24"
            style={{
              position: "absolute",
              left: cx,
              top: cy,
              opacity: cursorIn * (1 - kf(f, [PRESS + 10, PRESS + 18], [0, 1])),
              transform: `scale(${pressed ? 0.88 : 1})`,
              filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.6))",
            }}
          >
            <path d="M4 2 L4 19 L8.6 14.8 L11.6 21.5 L14.4 20.3 L11.4 13.7 L17.6 13.5 Z" fill="#fff" stroke="#111" strokeWidth={1.2} strokeLinejoin="round" />
          </svg>

          {/* The build, as captured from the running app. */}
          <div style={{ position: "absolute", inset: 0, opacity: toBuild }}>
            <Full src={buildSrc(i)} />
            {mix > 0 && i + 1 < BUILD_STATES ? <Full src={buildSrc(i + 1)} opacity={mix} /> : null}
            <div
              style={{
                ...box(ui.status, 0),
                left: 24,
                width: 140,
                border: `2px solid ${colors.accent}`,
                borderRadius: 8,
                boxShadow: "0 0 28px rgba(246,128,32,0.4)",
                opacity: statusRing,
              }}
            />
          </div>
        </BrowserFrame>
      </div>
    </AbsoluteFill>
  );
};
