# Vectron product video

A 23-second product video built with [Remotion](https://www.remotion.dev) (React).
The rendered file is `out/vectron-promo.mp4`; the shot list is in
[STORYBOARD.md](STORYBOARD.md).

```bash
npm install
npm run studio    # live preview with a timeline, at http://localhost:3000
npm run render    # writes out/vectron-promo.mp4 (about 1–2 minutes)
```

The first render downloads a headless Chrome. To use one you already have, add
`--browser-executable=/path/to/chrome` to the render command.

## Changing things

| To change | Edit |
|---|---|
| **Copy:** every line of text, the crew roles, the stats, the tagline, the integration list, the Roadmap tag | `src/content.ts` |
| **Colours, fonts, type sizes, shadow** | `src/theme.ts` |
| **Duration:** the length of each scene, in frames at 30 fps | `src/timing.ts` |
| **Screenshots** | `public/ui/`, listed in `src/content.ts` under `assets` |

- **Copy.** Headlines are arrays of lines, so you control every line break. Keep each line short enough to fit its column; the studio preview shows you straight away.
- **Duration.** Later scenes shift automatically, and the beats inside a scene are placed relative to its length. The video is 690 frames (23s) at the default settings.
- **Colours.** The orange accent is `colors.accent`.
- **Fonts.** These are bundled in `public/fonts/` and loaded in `src/lib/fonts.ts`. Swap a `.woff2` file there to change typeface.
- **Integrations.** Edit the `integrations` list; each side holds up to five chips. Set `copy.integrate.tag` to `""` once they ship.

### Updating the screenshots

The product footage was captured from the running app. When the UI changes, re-capture it:

```bash
cd backend && VECTRON_PACING_SECONDS=1.0 uv run vectron serve   # terminal 1
cd video && npm i --no-save playwright && npx playwright install chromium
node scripts/capture.mjs                                         # terminal 2
```

The script prints how many brief and build frames it took. Copy those numbers into `assets.briefFrames` and `assets.buildFrames` in `src/content.ts`. If a crew role then ticks too early or late, adjust its `at` value (an index into the build frames).

## How it's put together

- **`src/Video.tsx`** places each scene on the timeline. A single `ProductStage` (the browser) runs under Describe, Build and the start of Deliver, so the camera move and the screen changes carry across scene cuts.
- **`src/scenes/`** has one file per scene. **`src/components/`** holds the shared pieces: background, browser frame, step label, text reveal, card and logo mark.
- **`src/lib/buildClock.ts`** keeps the role list in Build in step with the captured build frames.
