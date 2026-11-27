/** Scene 7: run 1 vs run 2 from src/data/scoreboard.json, then the misses. */
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import sb from './data/scoreboard.json';

const Bar = ({ label, a, aOf, b, bOf, at, good }: { label: string; a: number; aOf: number; b: number; bOf: number; at: number; good: boolean }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const p = spring({ frame: frame - at, fps, config: { damping: 20 } });
  const W = 1000;
  return (
    <div style={{ marginTop: 40, opacity: p }}>
      <div style={{ fontSize: 38, color: '#e2e8f0', marginBottom: 12 }}>{label}</div>
      {([['run 1', a, aOf, '#475569'], ['run 2', b, bOf, good ? '#22c55e' : '#f59e0b']] as [string, number, number, string][]).map(([name, v, of, col]) => (
        <div key={name} style={{ display: 'flex', alignItems: 'center', gap: 20, marginTop: 8 }}>
          <div style={{ width: 120, fontSize: 30, color: '#94a3b8' }}>{name}</div>
          <div style={{ height: 40, width: (W * v / of) * p, background: col, borderRadius: 8, minWidth: 4 }} />
          <div style={{ fontSize: 36, fontWeight: 700 }}>{Math.round(v * p)}/{of}</div>
        </div>
      ))}
    </div>
  );
};

export const Scoreboard = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const r1 = sb.run1; const r2 = sb.run2;
  const missAt = durationInFrames - 5 * fps;
  const miss = interpolate(frame, [missAt, missAt + 15], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <AbsoluteFill style={{ background: '#0b1020', fontFamily: 'Inter, Helvetica, Arial', color: 'white', padding: '70px 160px' }}>
      <div style={{ fontSize: 52, fontWeight: 800 }}>Measured before believed</div>
      <div style={{ fontSize: 30, color: '#94a3b8', marginTop: 8 }}>
        {r2.cases} real Commons Lang bugs with known origins, the same in both runs · {r2.controls} fresh reports that are not bugs per run
      </div>
      <Bar label="Exact commit found" a={r1.exact} aOf={r1.cases} b={r2.exact} bOf={r2.cases} at={3 * fps} good />
      <Bar label="Right when confident" a={r1.exact} aOf={r1.confident} b={r2.exact} bOf={r2.confident} at={Math.round(13 * fps)} good />
      <div style={{ position: 'absolute', right: 160, bottom: 250, width: 620, padding: 28, borderRadius: 18,
        background: '#1f2937', borderLeft: '10px solid #f59e0b', opacity: miss, fontSize: 30, lineHeight: 1.4 }}>
        Misses are published: {r2.confidentWrong} confident wrong answer (a renamed method),
        {' '}{r2.falseConfidence} control taken for a bug.
      </div>
    </AbsoluteFill>
  );
};
