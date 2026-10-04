# vectron.ai product video: storyboard

16:9, 1920×1080, 30 fps, 23 seconds. For developers, technical buyers and investors.
The story: **one sentence in, a complete, inspected system out**, using real
footage of the app.

| # | Time | What the viewer sees | What they should understand | On-screen copy | Into the next scene |
|---|---|---|---|---|---|
| 1 Hook | 0.0–2.7s | Black blueprint grid; the Vectron mark draws itself; two lines rise in. | The promise, before any UI. | "One brief in. / A complete system out." | The lines lift away as a browser rises from below. |
| 2 Describe | 2.7–7.0s | The real catalog in a browser (full view), then the camera pushes into the Mission Brief. The rest of the UI dims, the brief types itself, and the cursor presses **Build from brief**. | Starting a build is one sentence and one click. | "01 Describe: Describe it in one sentence." | The button press dissolves into the job page while the camera pulls back to the right. |
| 3 Build | 7.0–11.7s | Split: copy on the left, the captured build playing on the right. Each crew role ticks as its stage appears on screen, the camera moves closer to the assembly line, and the status is ringed when it reads SUCCEEDED. | Agents do the architecture and fabrication, visibly and in order. | "02 Build: A crew of agents builds it." "Offline by default, or powered by Claude." Roles: Commander → Quartermaster. | The browser recedes and blurs; output cards come forward from it. |
| 4 Deliver | 11.7–16.0s | Three layered cards (module source, the dimensioned airframe drawing, the inspection report) with the copy on the right. | You get real deliverables, not a demo. | "03 Deliver: Diagrams, code and tests. Ready to ship." 7 diagrams · 58 files · 13 modules · Inspection passed | The cards fold into one tile at the centre. |
| 5 Integrate | 16.0–19.3s | Wide, symmetric composition: the build tile as a hub, lines drawing out to integration chips in two groups. | It fits into existing engineering and autonomy toolchains. | "04 Integrate: Plugs into your stack." Tag: Roadmap | The chips retract and the hub's mark rises. |
| 6 Close | 19.3–23.0s | The Vectron mark, the tagline and a short descriptor; holds for about 2.5s. | Who this is for and what it stands for. | "Mission-ready systems, at the speed of command." "vectron.ai · Software factory for defense systems" | End. |

## Assumptions

- **Screens are real.** Every product screen is a screenshot of the running app, captured at 2× on the offline engine. The numbers shown (7 diagrams, 58 files, 13 modules, inspection passed with 1 warning) come from that build.
- **Integrations are not built yet.** They are shown as requested, with a small **Roadmap** tag so the video doesn't claim they ship today. Remove the tag in `src/content.ts` if you prefer.
- **The sans font is Figtree.** The landing page uses Avenir Next, which can't be bundled, so Figtree stands in as the closest free match. Labels use Chivo Mono, as on the site.
- **There is no soundtrack.** A music bed can be added with Remotion's `<Audio>` component in `src/Video.tsx`.
