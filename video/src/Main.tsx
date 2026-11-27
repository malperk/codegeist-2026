/** The whole video: one Series entry per narrated scene; each lasts as long as its narration. */
import { AbsoluteFill, Audio, Series, staticFile } from 'remotion';
import { Bisection } from './Bisection';
import { Captions } from './Captions';
import { Card } from './Card';
import { Checks } from './Checks';
import { Closing } from './Closing';
import { Scoreboard } from './Scoreboard';
import { ShotScene } from './ShotScene';
import scenes from './data/scenes.json';
import lang788 from '../public/shots/lang-788.json';
import commit from '../public/shots/commit-b82ab99.json';

export const FPS = 30;
const PAD = 0.7; // seconds of breathing room after each narration
const LEAD = 0.3; // seconds before the voice starts
export const frames = (i: number) => Math.round((scenes[i].seconds + PAD + LEAD) * FPS);
export const totalFrames = scenes.reduce((n, _, i) => n + frames(i), 0);

const Split = ({ parts }: { parts: [number, React.ReactNode][] }) => (
  <Series>{parts.map(([f, node], i) => <Series.Sequence key={i} durationInFrames={f}>{node}</Series.Sequence>)}</Series>
);

const visuals = (i: number): React.ReactNode => {
  const f = frames(i);
  switch (i) {
    case 0: return <ShotScene image="shots/lang-788.png" shot={lang788} keys={[
      { at: 0, target: 'full' }, { at: 3.5, target: 'summary', pad: 120, highlight: true },
      { at: 8.5, target: 'test', pad: 60, highlight: true }, { at: 15, target: 'created', pad: 260, highlight: true }]} />;
    case 1: return <Bisection mode="intro" />;
    case 2: return <Split parts={[
      [Math.round(f * 0.3), <Card image="shots/automation-rule.png" width={640} label="Jira Automation: on every new bug" />],
      [Math.round(f * 0.3), <Card image="shots/clang75-header.png" width={1100} label="The bug, as filed (CLANG-75, a mirror of LANG-788)" />],
      [f - 2 * Math.round(f * 0.3), <Card image="shots/clang75-agent-reply.png" width={900} label="The Rovo agent's reply" />]]} />;
    case 3: return <Checks />;
    case 4: return <Bisection mode="search" />;
    case 5: return <Split parts={[
      [Math.round(f * 0.4), <Card image="shots/clang75-result-top.png" width={1150} label="The result, posted on the issue" from={1.0} to={1.04} />],
      [f - Math.round(f * 0.4), <ShotScene image="shots/commit-b82ab99.png" shot={commit} keys={[
        { at: 0, target: 'title', pad: 300 }, { at: 2.5, target: 'message', pad: 80, highlight: true }, { at: 7, target: 'date', pad: 400, highlight: true }]} />]]} />;
    case 6: return <Scoreboard />;
    default: return <Closing />;
  }
};

export const Main = () => (
  <AbsoluteFill style={{ background: '#0b1020' }}>
    <Series>
      {scenes.map((s, i) => (
        <Series.Sequence key={s.id} durationInFrames={frames(i)}>
          {visuals(i)}
          <Series>
            <Series.Sequence offset={Math.round(LEAD * FPS)} durationInFrames={frames(i) - Math.round(LEAD * FPS)}>
              <Audio src={staticFile(s.audio)} />
              <Captions sentences={s.captions} seconds={s.seconds} />
            </Series.Sequence>
          </Series>
        </Series.Sequence>
      ))}
    </Series>
  </AbsoluteFill>
);
