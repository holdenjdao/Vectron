import { loadFont } from "@remotion/fonts";
import { staticFile } from "remotion";

// Bundled fonts so every render looks the same, online or not.
const faces = [
  { family: "Figtree", weight: "400", file: "figtree-latin-400-normal.woff2" },
  { family: "Figtree", weight: "600", file: "figtree-latin-600-normal.woff2" },
  { family: "Figtree", weight: "700", file: "figtree-latin-700-normal.woff2" },
  { family: "Chivo Mono", weight: "400", file: "chivo-mono-latin-400-normal.woff2" },
  { family: "Chivo Mono", weight: "500", file: "chivo-mono-latin-500-normal.woff2" },
];

export const fontsReady = Promise.all(
  faces.map((f) =>
    loadFont({ family: f.family, url: staticFile(`fonts/${f.file}`), weight: f.weight, format: "woff2" }),
  ),
);
