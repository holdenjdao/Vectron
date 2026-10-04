import { useId } from "react";

/** vectron.ai mark ("Delta"): a folded, asymmetric delta wing in the Thermal palette. */
export function Logo({ size = 22 }: { size?: number }) {
  // useId() contains colons, which an SVG url(#…) reference cannot always resolve.
  const heat = `heat${useId().replace(/[^a-zA-Z0-9]/g, "")}`;
  return (
    <svg
      className="brand__mark"
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-hidden="true"
      focusable="false"
    >
      <defs>
        <linearGradient id={heat} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0" stopColor="#ff5a1f" />
          <stop offset="1" stopColor="#ffc24b" />
        </linearGradient>
      </defs>
      <path d="M3 15 L17 14 L32 43 L28 55 Z" fill="#b3260c" />
      <path d="M28 55 L32 43 L47 11 L61 5 Z" fill={`url(#${heat})`} />
    </svg>
  );
}
