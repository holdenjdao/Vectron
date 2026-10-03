// Re-captures the product screenshots in public/ui from a running Vectron.
//
//   cd backend && VECTRON_PACING_SECONDS=1.0 uv run vectron serve   # in one terminal
//   cd video && npm i --no-save playwright && npx playwright install chromium
//   node scripts/capture.mjs                                         # in another
//
// Set CHROMIUM_PATH to use an existing browser, UI_DIR to write somewhere other
// than public/ui. Everything is captured at 2× from a 1440×900 window, so
// close-ups stay sharp at 1080p.

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const APP = process.env.VECTRON_URL ?? "http://127.0.0.1:8000";
const BRIEF = "Small recon drone for night-time perimeter surveillance, with waypoint missions and a geofence";
const OUT = process.env.UI_DIR ?? path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "public", "ui");

const browser = await chromium.launch(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {});
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
const jpg = (file, quality = 90) => page.screenshot({ path: path.join(OUT, file), type: "jpeg", quality });
const shoot = (locator, file) => locator.screenshot({ path: path.join(OUT, file), type: "jpeg", quality: 90 });
const pad = (n) => String(n).padStart(3, "0");
for (const dir of ["brief", "build"]) {
  fs.rmSync(path.join(OUT, dir), { recursive: true, force: true });
  fs.mkdirSync(path.join(OUT, dir), { recursive: true });
}
const meta = {};

// Catalog, then the brief panel as the brief is typed, three characters at a time.
await page.goto(`${APP}/app/`, { waitUntil: "networkidle" });
await jpg("catalog.jpg");
const brief = page.locator("section.panel").filter({ hasText: /mission brief/i }).first();
const textarea = page.locator("textarea").first();
meta.briefPanel = await brief.boundingBox();
meta.buildButton = await page.getByRole("button", { name: /build from brief/i }).boundingBox();
await shoot(brief, "brief/000.jpg");
await textarea.click();
let n = 0;
for (let i = 0; i < BRIEF.length; i += 3) {
  await textarea.pressSequentially(BRIEF.slice(i, i + 3));
  await shoot(brief, `brief/${pad(++n)}.jpg`);
}
meta.briefFrames = n + 1;
await page.mouse.move(-10, -10);
await jpg("catalog-brief.jpg");

// The build, screen by screen until the job finishes.
await page.getByRole("button", { name: /build from brief/i }).click();
await page.waitForURL(/#\/jobs\//);
const jobId = decodeURIComponent(page.url().split("#/jobs/")[1]);
let k = 0;
for (;;) {
  await jpg(`build/${pad(k++)}.jpg`, 82);
  const job = await (await fetch(`${APP}/api/jobs/${jobId}`)).json();
  if (!["queued", "pending", "running"].includes(job.status) || k > 150) break;
  await page.waitForTimeout(200);
}
meta.buildFrames = k;
await page.waitForTimeout(1500);
await jpg("job-done.jpg", 82);

// Close-ups of the outputs.
await shoot(page.locator("article.diagram-card .diagram-canvas").first(), "diagram-airframe.jpg");
const panel = () => page.locator("[role=tabpanel]:visible").first();
await page.getByRole("tab", { name: /^inspection/i }).click();
await page.waitForTimeout(800);
await shoot(panel(), "inspection-panel.jpg");
await page.getByRole("tab", { name: /^code/i }).click();
await page.waitForTimeout(800);
await page.getByText("motor_mixer.py", { exact: true }).first().click();
await page.waitForTimeout(1000);
await shoot(panel(), "code-panel.jpg");

fs.writeFileSync(path.join(OUT, "capture-meta.json"), JSON.stringify(meta, null, 1));
console.log(`Captured ${meta.briefFrames} brief frames and ${meta.buildFrames} build frames into ${OUT}.`);
console.log("Update briefFrames, buildFrames and the ui boxes in src/content.ts if they changed.");
await browser.close();
