import { Easing, interpolate } from "remotion";

// One house curve for everything: fast out, long settle.
export const ease = Easing.bezier(0.16, 1, 0.3, 1);
export const easeInOut = Easing.bezier(0.65, 0, 0.35, 1);
export const easeIn = Easing.bezier(0.7, 0, 0.84, 0);

/** Interpolate across keyframes with clamping and the house easing. */
export const kf = (
  frame: number,
  frames: number[],
  values: number[],
  easing: (t: number) => number = ease,
) => interpolate(frame, frames, values, { easing, extrapolateLeft: "clamp", extrapolateRight: "clamp" });

/** 0 → 1 over `duration` frames starting at `start`. */
export const progress = (frame: number, start: number, duration: number, easing = ease) =>
  kf(frame, [start, start + duration], [0, 1], easing);

/** Fade/lift in at `start`, fade out ending at `end` (omit `end` to stay). */
export const inOut = (frame: number, start: number, end?: number, len = 16) => {
  const enter = progress(frame, start, len);
  const exit = end === undefined ? 0 : progress(frame, end - len, len, easeIn);
  return enter * (1 - exit);
};
