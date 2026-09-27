// Lazy Mermaid loader. The library (and its diagram chunks) is only fetched the
// first time a diagram is rendered, so the catalog stays light.

import type { MermaidConfig } from "mermaid";

type MermaidApi = (typeof import("mermaid"))["default"];

const FONT = 'Inter, "Segoe UI", Roboto, system-ui, sans-serif';

// Dark "tactical console" palette. Mermaid derives colours with khroma, so
// everything here is a plain hex value.
const THEME_VARIABLES = {
  darkMode: true,
  fontFamily: FONT,
  fontSize: "13px",
  background: "#0c131b",
  textColor: "#d7e3ee",
  titleColor: "#d7e3ee",
  lineColor: "#6d8aa5",

  primaryColor: "#112233",
  primaryTextColor: "#d7e3ee",
  primaryBorderColor: "#38e0a0",
  secondaryColor: "#0f2230",
  secondaryTextColor: "#d7e3ee",
  secondaryBorderColor: "#4cc2ff",
  tertiaryColor: "#0e1822",
  tertiaryTextColor: "#d7e3ee",
  tertiaryBorderColor: "#27405a",

  // Flowcharts / class diagrams
  mainBkg: "#112233",
  nodeBorder: "#38e0a0",
  nodeTextColor: "#d7e3ee",
  clusterBkg: "#0b1620",
  clusterBorder: "#27405a",
  edgeLabelBackground: "#0c131b",
  classText: "#d7e3ee",

  // Sequence diagrams
  actorBkg: "#112233",
  actorBorder: "#4cc2ff",
  actorTextColor: "#d7e3ee",
  actorLineColor: "#35506a",
  signalColor: "#9fb4c8",
  signalTextColor: "#d7e3ee",
  labelBoxBkgColor: "#101a24",
  labelBoxBorderColor: "#27405a",
  labelTextColor: "#d7e3ee",
  loopTextColor: "#8397ab",
  noteBkgColor: "#1c1a12",
  noteBorderColor: "#f5b841",
  noteTextColor: "#efd9a6",
  activationBkgColor: "#16283a",
  activationBorderColor: "#4cc2ff",
  sequenceNumberColor: "#070b10",

  // State diagrams
  stateBkg: "#112233",
  stateLabelColor: "#d7e3ee",
  labelBackgroundColor: "#0c131b",
  transitionColor: "#6d8aa5",
  transitionLabelColor: "#b8c9d9",
  compositeBackground: "#0b1620",
  compositeTitleBackground: "#101a24",
  altBackground: "#0e1822",
  specialStateColor: "#38e0a0",
  innerEndBackground: "#38e0a0",

  // Mindmaps (product breakdown): root node, then one colour per branch.
  git0: "#1d4f73",
  gitBranchLabel0: "#e6f1ff",
  ...Object.fromEntries(
    ["#16324a", "#12372c", "#3a2f12", "#2a2140", "#3a1f24", "#123a3a"].flatMap((fill, i) => [
      [`cScale${i}`, fill],
      [`cScale${i + 6}`, fill],
      [`cScaleLabel${i}`, "#e6f1ff"],
      [`cScaleLabel${i + 6}`, "#e6f1ff"],
    ]),
  ),

  errorBkgColor: "#3a1418",
  errorTextColor: "#ff5f5f",
};

const CONFIG: MermaidConfig = {
  startOnLoad: false,
  securityLevel: "strict",
  theme: "base",
  themeVariables: THEME_VARIABLES,
  fontFamily: FONT,
  suppressErrorRendering: true,
  flowchart: { curve: "basis", padding: 12 },
  sequence: { mirrorActors: false },
};

let loader: Promise<MermaidApi> | null = null;

function loadMermaid(): Promise<MermaidApi> {
  loader ??= import("mermaid")
    .then(({ default: mermaid }) => {
      mermaid.initialize(CONFIG);
      return mermaid;
    })
    .catch((err: unknown) => {
      loader = null; // allow a retry (e.g. chunk failed to load)
      throw err;
    });
  return loader;
}

let counter = 0;

/**
 * Renders Mermaid source to an SVG string (sanitised by Mermaid in strict
 * mode). Every call uses a fresh element id so the same diagram can be shown
 * twice (card + full-screen view) without clashing ids. Throws on syntax errors.
 */
export async function renderMermaid(source: string): Promise<string> {
  const mermaid = await loadMermaid();
  counter += 1;
  const id = `vx-mermaid-${counter}`;
  try {
    const { svg } = await mermaid.render(id, source);
    return svg;
  } finally {
    // Mermaid measures inside a scratch node in <body>; never leave it behind.
    document.getElementById(`d${id}`)?.remove();
  }
}
