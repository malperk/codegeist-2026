/** A crisp crop of a real page, floating on the dark background with a slow push-in. */
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

export const Card = ({ image, width, label, from = 1.0, to = 1.05 }:
  { image: string; width: number; label?: string; from?: number; to?: number }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 18 } });
  const s = interpolate(frame, [0, durationInFrames], [from, to]);
  return (
    <AbsoluteFill style={{ background: 'radial-gradient(circle at 30% 20%, #1e293b, #0b1020 70%)',
      alignItems: 'center', justifyContent: 'center' }}>
      {label && (
        <div style={{ position: 'absolute', top: 56, left: 80, fontSize: 34, color: '#94a3b8',
          fontFamily: 'Inter, Helvetica, Arial', letterSpacing: 1 }}>{label}</div>
      )}
      <div style={{ transform: `scale(${s * (0.94 + 0.06 * enter)}) translateY(${(1 - enter) * 40}px)`, opacity: enter,
        borderRadius: 22, overflow: 'hidden', boxShadow: '0 30px 80px rgba(0,0,0,0.55)', background: 'white', marginBottom: 90 }}>
        <Img src={staticFile(image)} style={{ width, display: 'block' }} />
      </div>
    </AbsoluteFill>
  );
};
