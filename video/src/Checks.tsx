/** Scene 4: the three real checks of LANG-D4J-45 (src/data/checks.json), one after another. */
import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import data from './data/checks.json';

const STYLE: Record<string, { color: string; title: string }> = {
  NOCOMPILE: { color: '#94a3b8', title: 'does not compile' },
  FAIL: { color: '#ef4444', title: 'fails, as the report says' },
  PASS: { color: '#22c55e', title: 'passes: does not reproduce' },
};

export const Checks = () => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const step = Math.floor((durationInFrames - fps) / data.checks.length);
  return (
    <AbsoluteFill style={{ background: '#0b1020', fontFamily: 'Inter, Helvetica, Arial', color: 'white', padding: '90px 140px' }}>
      <div style={{ fontSize: 40, color: '#94a3b8' }}>check-test on the reported revision · {data.issue}</div>
      {data.checks.map((c, i) => {
        const s = spring({ frame: frame - i * step, fps, config: { damping: 16 } });
        const st = STYLE[c.result];
        return (
          <div key={i} style={{ marginTop: 34, padding: '26px 34px', borderRadius: 18, background: '#111827',
            borderLeft: `10px solid ${st.color}`, opacity: s, transform: `translateX(${(1 - s) * 80}px)` }}>
            <div style={{ fontSize: 44, fontWeight: 700 }}>
              Attempt {i + 1}: <span style={{ color: st.color }}>{st.title}</span>
              <span style={{ fontSize: 30, color: '#64748b', marginLeft: 20 }}>{c.seconds} s</span>
            </div>
            <div style={{ fontSize: 28, fontFamily: 'Menlo, monospace', color: '#cbd5e1', marginTop: 12, lineHeight: 1.35 }}>
              {c.line.replace(/^src\/test\/\S+?:(\d+): /, 'line $1: ')}
            </div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
