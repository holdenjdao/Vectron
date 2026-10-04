import { AbsoluteFill, useCurrentFrame } from "remotion";

import { colors } from "../theme";

/** The one backdrop for the whole piece: near-black, a slow blueprint grid and a soft blue glow. */
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const drift = frame * 0.12;
  // The glow wanders slowly so the frame never looks frozen.
  const gx = 62 + Math.sin(frame / 120) * 8;
  const gy = 38 + Math.cos(frame / 150) * 6;
  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      <AbsoluteFill
        style={{
          background: `radial-gradient(ellipse 60% 55% at ${gx}% ${gy}%, ${colors.glow}, transparent 70%),
            radial-gradient(ellipse 45% 40% at 12% 100%, rgba(255, 194, 75, 0.06), transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(${colors.grid} 1px, transparent 1px),
            linear-gradient(90deg, ${colors.grid} 1px, transparent 1px)`,
          backgroundSize: "80px 80px",
          backgroundPosition: `${drift}px ${drift * 0.6}px`,
          maskImage: "radial-gradient(ellipse 85% 80% at 50% 45%, #000 25%, transparent 80%)",
          WebkitMaskImage: "radial-gradient(ellipse 85% 80% at 50% 45%, #000 25%, transparent 80%)",
        }}
      />
      <AbsoluteFill
        style={{ background: "radial-gradient(ellipse 120% 100% at 50% 50%, transparent 55%, rgba(0,0,0,0.55))" }}
      />
    </AbsoluteFill>
  );
};
