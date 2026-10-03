// Scene lengths in frames at 30 fps. Change a number here and every scene
// after it moves; beats inside a scene are placed relative to its length.

export const FPS = 30;

export const durations = {
  hook: 80,
  describe: 130,
  build: 140,
  deliver: 130,
  integrate: 100,
  close: 110,
};

type SceneName = keyof typeof durations;

const order: SceneName[] = ["hook", "describe", "build", "deliver", "integrate", "close"];

export const starts = order.reduce(
  (acc, name, i) => {
    acc[name] = i === 0 ? 0 : acc[order[i - 1]] + durations[order[i - 1]];
    return acc;
  },
  {} as Record<SceneName, number>,
);

export const TOTAL_FRAMES = order.reduce((sum, name) => sum + durations[name], 0);
