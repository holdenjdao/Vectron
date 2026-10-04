import { useId } from "react";

/** The vectron.ai mark ("Delta"): a folded, asymmetric delta wing in heat colours. */
export const VectronMark: React.FC<{ size: number; draw?: number }> = ({ size, draw = 1 }) => {
  // `draw` (0–1) brings the mark in: the dark left facet first, then the heat facet sweeps up.
  const heat = `heat${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  const left = Math.min(1, Math.max(0, draw * 2));
  const right = Math.min(1, Math.max(0, draw * 2 - 1));
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none">
      <defs>
        <linearGradient id={heat} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="#ff5a1f" />
          <stop offset="1" stopColor="#ffc24b" />
        </linearGradient>
      </defs>
      <path d="M3 15 L17 14 L32 43 L28 55 Z" fill="#b3260c" opacity={left} />
      <path
        d="M28 55 L32 43 L47 11 L61 5 Z"
        fill={`url(#${heat})`}
        opacity={right}
        transform={`translate(${(1 - right) * -6} ${(1 - right) * 8})`}
      />
    </svg>
  );
};
