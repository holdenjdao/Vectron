import { Composition } from "remotion";

import "./lib/fonts";
import { FPS, TOTAL_FRAMES } from "./timing";
import { Video } from "./Video";

export const RemotionRoot: React.FC = () => (
  <Composition id="VectronPromo" component={Video} durationInFrames={TOTAL_FRAMES} fps={FPS} width={1920} height={1080} />
);
