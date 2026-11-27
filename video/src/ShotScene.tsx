/**
 * A sharp page capture with a camera: keyframes name an element box recorded by capture/shoot.py
 * (or "full"), and the camera eases from one framing to the next.
 */
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

export type Shot = { width: number; height: number; boxes: Record<string, number[]> };
export type Key = { at: number; target: string; pad?: number; highlight?: boolean };

const W = 1920; const H = 1080;

function framing(shot: Shot, target: string, pad = 80) {
  const [x, y, w, h] = target === 'full' ? [0, 0, shot.width, shot.height] : shot.boxes[target];
  const s = Math.min(W / (w + 2 * pad), H / (h + 2 * pad), 2.2);
  return { s, cx: x + w / 2, cy: y + h / 2 };
}

export const ShotScene = ({ image, shot, keys }: { image: string; shot: Shot; keys: Key[] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  let k = 0;
  while (k < keys.length - 1 && t >= keys[k + 1].at) k += 1;
  const a = framing(shot, keys[k].target, keys[k].pad);
  const nextKey = keys[k + 1];
  const b = nextKey ? framing(shot, nextKey.target, nextKey.pad) : a;
  // Move during the 1.2 s before the next keyframe.
  const p = nextKey ? interpolate(t, [nextKey.at - 1.2, nextKey.at], [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.inOut(Easing.cubic) }) : 0;
  const s = a.s + (b.s - a.s) * p; const cx = a.cx + (b.cx - a.cx) * p; const cy = a.cy + (b.cy - a.cy) * p;
  // Keep the page edge from showing.
  const tx = Math.min(0, Math.max(W - shot.width * s, W / 2 - cx * s));
  const ty = Math.min(0, Math.max(H - shot.height * s, H / 2 - cy * s));
  const hl = keys[k].highlight && keys[k].target !== 'full' && p === 0 ? shot.boxes[keys[k].target] : null;
  return (
    <AbsoluteFill style={{ background: '#0b1020', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, transformOrigin: '0 0', transform: `translate(${tx}px, ${ty}px) scale(${s})` }}>
        <Img src={staticFile(image)} style={{ width: shot.width, height: shot.height, display: 'block' }} />
        {hl && (
          <div style={{ position: 'absolute', left: hl[0] - 12, top: hl[1] - 10, width: hl[2] + 24, height: hl[3] + 20,
            border: '6px solid #f59e0b', borderRadius: 14, boxShadow: '0 0 0 9999px rgba(2,6,23,0.35)' }} />
        )}
      </div>
    </AbsoluteFill>
  );
};
