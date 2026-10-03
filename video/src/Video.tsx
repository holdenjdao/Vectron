import { AbsoluteFill, Sequence } from "remotion";

import { Background } from "./components/Background";
import { BuildCopy } from "./scenes/BuildCopy";
import { Close } from "./scenes/Close";
import { Deliver } from "./scenes/Deliver";
import { DescribeCopy } from "./scenes/DescribeCopy";
import { Hook } from "./scenes/Hook";
import { Integrate } from "./scenes/Integrate";
import { ProductStage } from "./scenes/ProductStage";
import { durations, starts } from "./timing";

/** The whole piece. One background; the browser stage runs under Describe, Build and Deliver. */
export const Video: React.FC = () => (
  <AbsoluteFill>
    <Background />
    <Sequence name="Hook" from={starts.hook} durationInFrames={durations.hook}>
      <Hook />
    </Sequence>
    <Sequence
      name="Product stage"
      from={starts.describe}
      durationInFrames={durations.describe + durations.build + 24}
    >
      <ProductStage />
    </Sequence>
    <Sequence name="Describe" from={starts.describe} durationInFrames={durations.describe}>
      <DescribeCopy />
    </Sequence>
    <Sequence name="Build" from={starts.build} durationInFrames={durations.build}>
      <BuildCopy />
    </Sequence>
    <Sequence name="Deliver" from={starts.deliver} durationInFrames={durations.deliver}>
      <Deliver />
    </Sequence>
    <Sequence name="Integrate" from={starts.integrate} durationInFrames={durations.integrate}>
      <Integrate />
    </Sequence>
    <Sequence name="Close" from={starts.close} durationInFrames={durations.close}>
      <Close />
    </Sequence>
  </AbsoluteFill>
);
