/** Burned-in captions: each sentence gets screen time in proportion to its length. */
import { useCurrentFrame, useVideoConfig } from 'remotion';

export const Captions = ({ sentences, seconds, delay = 0 }: { sentences: string[]; seconds: number; delay?: number }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = sentences.reduce((n, s) => n + s.length, 0);
  let t = (frame - delay) / fps;
  if (t < 0 || t > seconds) return null;
  let i = 0;
  for (; i < sentences.length; i += 1) {
    const d = (sentences[i].length / total) * seconds;
    if (t < d) break;
    t -= d;
  }
  const text = sentences[Math.min(i, sentences.length - 1)];
  return (
    <div style={{ position: 'absolute', bottom: 48, left: 0, right: 0, display: 'flex', justifyContent: 'center' }}>
      <div style={{ maxWidth: 1500, padding: '14px 28px', borderRadius: 14, background: 'rgba(2,6,23,0.82)',
        color: 'white', fontSize: 40, lineHeight: 1.3, textAlign: 'center', fontFamily: 'Inter, Helvetica, Arial' }}>
        {text}
      </div>
    </div>
  );
};
