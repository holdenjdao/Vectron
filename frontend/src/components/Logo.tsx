/** Vectron mark: an abstract vector arrowhead formed by nested chevrons. */
export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg
      className="brand__mark"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M2.5 4.5 L12 20.5 L21.5 4.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.9"
        strokeLinecap="square"
        strokeLinejoin="miter"
      />
      <path d="M8 4.5 L12 11.4 L16 4.5 Z" fill="currentColor" />
    </svg>
  );
}
