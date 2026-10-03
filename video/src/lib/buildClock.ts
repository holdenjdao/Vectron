import { assets } from "../content";
import { durations } from "../timing";

// The captured build plays back over this window of the Build scene (frames
// local to that scene). The scene text and the browser both read this clock,
// so the role list ticks in step with the screen.
export const BUILD_PLAY = { start: 8, end: Math.round(durations.build * 0.74) };

/** Number of screens in the build sequence: the captured frames plus the finished page. */
export const BUILD_STATES = assets.buildFrames + 1;

/** Playback position, 0 … BUILD_STATES-1, for a frame local to the Build scene. */
export const buildPosition = (localFrame: number) => {
  const t = (localFrame - BUILD_PLAY.start) / (BUILD_PLAY.end - BUILD_PLAY.start);
  return Math.min(Math.max(t, 0), 1) * (BUILD_STATES - 1);
};
