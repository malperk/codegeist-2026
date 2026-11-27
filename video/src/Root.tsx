import { Composition } from 'remotion';
import { Bisection, bisectionFrames } from './Bisection';
import { FPS, Main, totalFrames } from './Main';

export const Root = () => (
  <>
    <Composition id="Main" component={Main} durationInFrames={totalFrames} fps={FPS} width={1920} height={1080} />
    <Composition id="Bisection" component={Bisection} durationInFrames={bisectionFrames} fps={30} width={1920} height={1080} />
  </>
);
