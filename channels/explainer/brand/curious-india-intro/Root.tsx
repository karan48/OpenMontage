import React from "react";
import { Composition } from "remotion";
import { Intro, INTRO_FRAMES } from "./Intro";

// The Curious India channel intro: ONE locked 3.0 s clip (90 frames @ 30 fps, 1920x1080).
// Rendered silent; the sting is muxed in afterwards (see ../README.md).
export const Root: React.FC = () => (
  <>
    <Composition
      id="CuriousIndiaIntro"
      component={Intro}
      durationInFrames={INTRO_FRAMES}
      fps={30}
      width={1920}
      height={1080}
    />
  </>
);
