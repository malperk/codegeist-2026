/**
 * Bisection scene, driven entirely by a recorded run (src/data/bisect-lang-788.json):
 * every probe, its result and the search window come from the real job, replayed round by round.
 */
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import run from './data/bisect-lang-788.json';

const COLORS: Record<string, string> = {
  PASS: '#22c55e', FAIL: '#ef4444', NOCOMPILE: '#94a3b8', ERROR: '#f59e0b',
};
const LABEL: Record<string, string> = {
  PASS: 'passes', FAIL: 'fails', NOCOMPILE: "can't compile yet", ERROR: 'unbuildable',
};
const INTRO = 75;     // title
const ROUND = 60;     // per search round: zoom, then probes land
const OUTRO = 120;    // answer card
export const bisectionFrames = INTRO + run.rounds.length * ROUND + OUTRO;

const W = 1600;       // timeline width in px
const X0 = 160;

export const Bisection = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame - INTRO;
  const r = Math.max(0, Math.min(run.rounds.length - 1, Math.floor(t / ROUND)));
  const inRound = t - r * ROUND;

  // Camera: the visible window [lo, hi] of commit indices, eased from one round's window to the next.
  const win = (k: number) => k < run.rounds.length
    ? [Math.max(0, run.rounds[k].lo), run.rounds[k].hi]
    : [run.final.lo - 1, run.final.hi + 1];
  const prev = win(Math.max(0, r)); const next = win(r + 1);
  const z = t < 0 ? 0 : interpolate(inRound, [ROUND - 18, ROUND], [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) });
  const done = t >= run.rounds.length * ROUND;
  const [lo, hi] = done ? win(run.rounds.length) : [prev[0] + (next[0] - prev[0]) * z, prev[1] + (next[1] - prev[1]) * z];
  const x = (i: number) => X0 + ((i - lo) / Math.max(1, hi - lo)) * W;

  const seen = run.rounds.slice(0, done ? run.rounds.length : r + 1).flatMap((rd, k) =>
    rd.probes.map((p, j) => ({ ...p, at: INTRO + k * ROUND + 6 + j * 5 })));
  const probesSoFar = seen.filter((p) => frame >= p.at).length + 1; // +1: the reported revision

  const titleOpacity = interpolate(frame, [0, 15, INTRO - 10, INTRO], [0, 1, 1, 0.0], { extrapolateRight: 'clamp' });
  const cardIn = spring({ frame: frame - (INTRO + run.rounds.length * ROUND), fps, config: { damping: 16 } });

  return (
    <AbsoluteFill style={{ background: '#0b1020', fontFamily: 'Inter, Helvetica, Arial', color: 'white' }}>
      <div style={{ position: 'absolute', top: 120, width: '100%', textAlign: 'center', opacity: titleOpacity }}>
        <div style={{ fontSize: 84, fontWeight: 800 }}>{run.total.toLocaleString('en-GB')} commits.</div>
        <div style={{ fontSize: 56, color: '#cbd5e1', marginTop: 12 }}>Which one broke it?</div>
      </div>

      {/* timeline */}
      <div style={{ position: 'absolute', left: X0, top: 560, width: W, height: 6, background: '#334155', borderRadius: 3 }} />
      {!done && t >= 0 && (
        <div style={{ position: 'absolute', top: 520, height: 86, left: x(run.rounds[r].lo < 0 ? lo : run.rounds[r].lo),
          width: x(run.rounds[r].hi) - x(run.rounds[r].lo < 0 ? lo : run.rounds[r].lo),
          background: 'rgba(99,102,241,0.18)', border: '2px solid rgba(129,140,248,0.7)', borderRadius: 10 }} />
      )}
      {/* reported revision: fails */}
      <Dot x={x(run.total - 1)} color={COLORS.FAIL} scale={1} label="reported" />
      {seen.map((p) => {
        const s = spring({ frame: frame - p.at, fps, config: { damping: 12 } });
        const visible = x(p.i) > X0 - 40 && x(p.i) < X0 + W + 40;
        return visible ? <Dot key={p.i} x={x(p.i)} color={COLORS[p.state]} scale={s} /> : null;
      })}

      {t >= 0 && !done && (
        <div style={{ position: 'absolute', top: 700, width: '100%', textAlign: 'center', fontSize: 44, color: '#e2e8f0' }}>
          Round {r + 1}: {run.rounds[r].hi - Math.max(0, run.rounds[r].lo)} commits left · 4 builds in parallel
        </div>
      )}
      <Legend />
      <div style={{ position: 'absolute', right: 80, top: 60, fontSize: 34, color: '#94a3b8' }}>
        test runs: {Math.min(probesSoFar, run.runs.length)}
      </div>

      {done && (
        <div style={{ position: 'absolute', left: 260, right: 260, top: 640, padding: '36px 48px', borderRadius: 24,
          background: '#111827', border: '2px solid #ef4444', transform: `scale(${cardIn})`, opacity: cardIn }}>
          <div style={{ fontSize: 40, color: '#fca5a5' }}>The test passes on the commit before, and fails from here on</div>
          <div style={{ fontSize: 64, fontWeight: 800, marginTop: 10, fontFamily: 'Menlo, monospace' }}>commit {run.answer}</div>
          <div style={{ fontSize: 34, color: '#cbd5e1', marginTop: 10 }}>{run.subject.split('.')[0]}.</div>
          <div style={{ fontSize: 32, color: '#94a3b8', marginTop: 18 }}>
            {run.runs.length} test runs · {Math.round(run.seconds)} s · confidence: high
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};

const Dot = ({ x, color, scale, label }: { x: number; color: string; scale: number; label?: string }) => (
  <div style={{ position: 'absolute', left: x - 18, top: 545, width: 36, height: 36, borderRadius: 18, background: color,
    transform: `scale(${scale})`, boxShadow: `0 0 24px ${color}` }}>
    {label && <div style={{ position: 'absolute', top: 50, left: -40, width: 120, textAlign: 'center', fontSize: 26, color: '#fca5a5' }}>{label}</div>}
  </div>
);

const Legend = () => (
  <div style={{ position: 'absolute', bottom: 70, width: '100%', display: 'flex', justifyContent: 'center', gap: 56, fontSize: 30 }}>
    {Object.keys(COLORS).map((k) => (
      <div key={k} style={{ display: 'flex', alignItems: 'center', gap: 14, color: '#cbd5e1' }}>
        <div style={{ width: 22, height: 22, borderRadius: 11, background: COLORS[k] }} /> test {LABEL[k]}
      </div>
    ))}
  </div>
);
