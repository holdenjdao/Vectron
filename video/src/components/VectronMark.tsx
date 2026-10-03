import { colors } from "../theme";

/** The Vectron mark from the landing page: a white V around an orange wedge. */
export const VectronMark: React.FC<{ size: number; draw?: number }> = ({ size, draw = 1 }) => {
  // `draw` (0–1) traces the V stroke; the wedge fills in over the last third.
  const length = 46;
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <path
        d="M4.5 7 L16 26.5 L27.5 7"
        stroke={colors.text}
        strokeWidth={3}
        strokeLinejoin="round"
        strokeLinecap="round"
        strokeDasharray={length}
        strokeDashoffset={length * (1 - draw)}
      />
      <path d="M11.5 7 L16 14.8 L20.5 7 Z" fill={colors.accent} opacity={Math.max(0, (draw - 0.66) * 3)} />
    </svg>
  );
};
