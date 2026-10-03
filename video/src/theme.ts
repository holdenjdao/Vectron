// Colours, fonts and type sizes. Matches the Vectron landing page: near-black,
// white type, one orange accent, blue only for the blueprint grid.

export const colors = {
  bg: "#0b0c10",
  bgRaised: "#12141b",
  text: "#ffffff",
  dim: "#9aa0aa",
  faint: "#5d636e",
  accent: "#f68020",
  grid: "rgba(99, 174, 255, 0.07)",
  glow: "rgba(0, 69, 217, 0.28)",
  line: "rgba(255, 255, 255, 0.12)",
  card: "#0f1218",
};

export const fonts = {
  sans: "Figtree, 'Helvetica Neue', Arial, sans-serif",
  mono: "'Chivo Mono', Menlo, Consolas, monospace",
};

// Sizes in px on the 1920×1080 frame. Nothing smaller than 22px, so labels
// stay readable when the video plays on a phone.
export const type = {
  hook: 128,
  headline: 64,
  sub: 30,
  label: 24,
  micro: 22,
};

export const shadow = "0 40px 120px rgba(0, 0, 0, 0.65), 0 12px 32px rgba(0, 0, 0, 0.45)";
