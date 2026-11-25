import { Composition } from 'remotion';
import { Bisection, bisectionFrames } from './Bisection';

export const Root = () => (
  <Composition id="Bisection" component={Bisection} durationInFrames={bisectionFrames}
    fps={30} width={1920} height={1080} />
);
