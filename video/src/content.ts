// Everything a non-developer is likely to edit: on-screen copy, the
// integration list and the screenshots each scene uses. All product numbers
// below come from a real build of the Recon Drone blueprint.

export const copy = {
  brand: "Vectron",
  brandLabel: "Vectron · Software factory",

  hook: ["One brief in.", "A complete system out."],

  describe: {
    step: "01",
    label: "Describe",
    headline: ["Describe it in one sentence."],
  },

  build: {
    step: "02",
    label: "Build",
    headline: ["A crew of agents", "builds it."],
    sub: "Offline by default, or powered by Claude.",
    // Lit in order as the build progresses. `at` is the build frame (0–15)
    // at which the role turns on.
    roles: [
      { name: "Commander", detail: "reads the brief", at: 1 },
      { name: "Architect", detail: "derives the spec", at: 3 },
      { name: "Draftsman", detail: "draws the diagrams", at: 5 },
      { name: "Integrator", detail: "wires the core", at: 6 },
      { name: "Engineers ×13", detail: "fabricate modules", at: 8 },
      { name: "Inspector", detail: "runs the checks", at: 13 },
      { name: "Quartermaster", detail: "packages the bundle", at: 15 },
    ],
  },

  deliver: {
    step: "03",
    label: "Deliver",
    headline: ["Diagrams, code", "and tests.", "Ready to ship."],
    stats: ["7 diagrams", "58 files", "13 modules", "Inspection passed"],
    cards: {
      diagram: "Airframe drawing",
      code: "Module source",
      inspection: "Inspection report",
    },
  },

  integrate: {
    step: "04",
    label: "Integrate",
    headline: ["Plugs into your stack."],
    // Shown next to the label. Set to "" to hide it.
    tag: "Roadmap",
    hub: "Vectron build",
  },

  close: {
    tagline: ["Mission-ready systems,", "at the speed of command."],
    footer: "Software factory for defense systems",
  },
};

// Integration chips, as two groups either side of the hub.
export const integrations = {
  left: { title: "Delivery", items: ["GitHub", "GitLab", "Jira", "Docker", "Kubernetes"] },
  right: { title: "Autonomy & sim", items: ["ROS 2", "PX4", "ArduPilot", "Gazebo", "MATLAB / Simulink"] },
};

// Real Vectron screenshots, captured at 2× from the running app (1440×900 viewport).
export const assets = {
  catalog: "ui/catalog.jpg",
  catalogWithBrief: "ui/catalog-brief.jpg",
  briefFrames: 33, // ui/brief/000.jpg … 032.jpg, the brief panel as it is typed
  buildFrames: 15, // ui/build/000.jpg … 014.jpg, the job page as the build runs
  jobDone: "ui/job-done.jpg",
  diagram: "ui/diagram-airframe.jpg",
  code: "ui/code-panel.jpg",
  inspection: "ui/inspection-panel.jpg",
};

// Where things sit in the 1440×900 app screenshots (CSS px), for camera moves
// and highlights. From ui/capture-meta.json.
export const ui = {
  viewport: { width: 1440, height: 900 },
  briefPanel: { x: 24, y: 224.5, width: 1028, height: 169.5 },
  buildButton: { x: 807, y: 345, width: 230, height: 34 },
  status: { x: 24, y: 194, width: 1392, height: 62 },
};
