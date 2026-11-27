import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const Closing = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 18 } });
  return (
    <AbsoluteFill style={{ background: 'radial-gradient(circle at 50% 30%, #1e293b, #0b1020 70%)', color: 'white',
      fontFamily: 'Inter, Helvetica, Arial', alignItems: 'center', justifyContent: 'center', textAlign: 'center' }}>
      <div style={{ opacity: s, transform: `scale(${0.9 + 0.1 * s})`, marginBottom: 80 }}>
        <div style={{ fontSize: 110, fontWeight: 800 }}>Bug Origin</div>
        <div style={{ fontSize: 44, color: '#cbd5e1', marginTop: 16 }}>File a bug. Get its origin, with the evidence.</div>
        <div style={{ fontSize: 32, color: '#94a3b8', marginTop: 50 }}>Rovo agent · Forge · Jira Automation · Cloud Run</div>
        <div style={{ fontSize: 32, color: '#94a3b8', marginTop: 14, fontFamily: 'Menlo, monospace' }}>github.com/malperk/codegeist-2026</div>
      </div>
    </AbsoluteFill>
  );
};
