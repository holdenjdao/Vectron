import { AbsoluteFill, useCurrentFrame } from "remotion";

import { RevealLines } from "../components/RevealLines";
import { StepLabel } from "../components/StepLabel";
import { copy } from "../content";
import { inOut } from "../lib/anim";
import { colors, type } from "../theme";
import { durations } from "../timing";

/** 2 · Describe: label over the full view, headline once the camera is on the brief. */
export const DescribeCopy: React.FC = () => {
  const frame = useCurrentFrame();
  const end = durations.describe;
  const c = copy.describe;
  // A scrim keeps the headline readable over the dimmed app.
  const scrim = inOut(frame, 40, end - 2, 18);
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          opacity: scrim,
          background: `linear-gradient(180deg, ${colors.bg} 0%, rgba(15,10,10,0.86) 300px, rgba(15,10,10,0) 470px)`,
        }}
      />
      <div style={{ position: "absolute", left: 120, top: 70 }}>
        <StepLabel step={c.step} label={c.label} start={10} exit={end - 4} />
      </div>
      <div style={{ position: "absolute", left: 120, top: 150 }}>
        <RevealLines lines={c.headline} start={46} exit={end - 4} size={type.headline} />
      </div>
    </AbsoluteFill>
  );
};
