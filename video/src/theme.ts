// Colours, fonts and type sizes. The Thermal palette, as on the vectron.ai
// landing page: warm black, cream type, heat orange, amber for the grid.

export const colors = {
  bg: "#0f0a0a",
  bgRaised: "#1c1212",
  text: "#fff4ec",
  dim: "#a3958d",
  faint: "#5f524c",
  accent: "#ff5a1f",
  grid: "rgba(255, 194, 75, 0.06)",
  glow: "rgba(179, 38, 12, 0.32)",
  line: "rgba(255, 244, 236, 0.12)",
  card: "#140d0d",
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
