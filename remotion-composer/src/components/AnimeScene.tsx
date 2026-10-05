import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ParticleOverlay, type ParticleType } from "./ParticleOverlay";

/**
 * Resolve asset path — use staticFile() for local paths, passthrough URLs.
 * Duplicated from Explainer.tsx to keep the component self-contained.
 */
function resolveAsset(src: string): string {
  if (
    src.startsWith("http://") ||
    src.startsWith("https://") ||
    src.startsWith("data:")
  ) {
    return src;
  }
  const clean = src.replace(/^file:\/\/\/?/, "");
  return staticFile(clean);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type CameraMotion =
  | "zoom-in"
  | "zoom-out"
  | "pan-left"
  | "pan-right"
  | "ken-burns"
  | "drift-up"
  | "drift-down"
  | "parallax"
  | "static";

/**
 * A timed switch to one of the scene's images, so an expression change, a
 * blink or a mouth movement lands on a spoken word instead of at an evenly
 * spaced point. Times usually come from forced-alignment word onsets.
 */
export interface AnimeCue {
  /** Index into `images` to show from `at` onwards */
  image: number;
  /** Seconds from the start of the scene */
  at: number;
  /** Fade-in seconds over the image it replaces (default 0.25; ~0.06 for a blink, 0 for a hard cut) */
  fade?: number;
}

const DEFAULT_CUE_FADE = 0.25;

/**
 * Which image is current at time `t` (seconds) under a cue schedule, which
 * one it is fading in over, and how far the fade has got. images[0] shows
 * until the first cue. Invalid cues (unknown image, non-finite time) are
 * ignored; a cue to the image already showing is a no-op.
 */
export function cueLayers(
  cues: AnimeCue[],
  imageCount: number,
  t: number
): { current: number; previous: number | null; progress: number } {
  const valid = cues
    .filter(
      (c) =>
        Number.isInteger(c.image) &&
        c.image >= 0 &&
        c.image < imageCount &&
        Number.isFinite(c.at)
    )
    .sort((a, b) => a.at - b.at);
  let current = 0;
  let previous: number | null = null;
  let progress = 1;
  for (const cue of valid) {
    if (cue.at > t) break;
    if (cue.image === current) continue;
    const fade = Math.max(0, cue.fade ?? DEFAULT_CUE_FADE);
    previous = current;
    current = cue.image;
    progress = fade === 0 ? 1 : Math.min(1, (t - cue.at) / fade);
  }
  return { current, previous: progress >= 1 ? null : previous, progress };
}

export interface AnimeSceneProps {
  /** Image paths. Without `cues`: 1-4 images crossfaded at even intervals. With `cues`: any number, switched at the cue times */
  images: string[];
  /**
   * Timed image switches (seconds from the scene start). When set, replaces the
   * even crossfade schedule: images[0] shows until the first cue, and each cue
   * fades its image in on top of the previous one. Keep cues at least one fade apart.
   */
  cues?: AnimeCue[];
  /** Camera motion applied to all image layers */
  animation?: CameraMotion;
  /** Particle effect overlay */
  particles?: ParticleType;
  /** Particle color (default: warm yellow) */
  particleColor?: string;
  /** Number of particles (default: 20) */
  particleCount?: number;
  /** Particle opacity multiplier 0-1 (default: 0.6) */
  particleIntensity?: number;
  /** Scene background color behind images (default: dark navy) */
  backgroundColor?: string;
  /** Show cinematic vignette (default: true) */
  vignette?: boolean;
  /** Starting gradient color for animated lighting shift */
  lightingFrom?: string;
  /** Ending gradient color for animated lighting shift */
  lightingTo?: string;
  /**
   * Actual scene duration in seconds.
   * CRITICAL: useVideoConfig().durationInFrames returns the FULL composition
   * duration, not the Sequence duration. This prop provides the real scene
   * length so crossfade/camera/lighting calculations use the correct range.
   */
  sceneDurationSeconds?: number;
}

// ---------------------------------------------------------------------------
// Cinematic vignette — slightly stronger than the Explainer default
// ---------------------------------------------------------------------------

const AnimeVignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        "radial-gradient(ellipse at center, transparent 35%, rgba(0,0,0,0.6) 100%)",
      pointerEvents: "none",
    }}
  />
);

// ---------------------------------------------------------------------------
// Camera motion calculator
// ---------------------------------------------------------------------------

function useCameraMotion(animation: CameraMotion, effectiveDuration: number) {
  const frame = useCurrentFrame();

  const progress = interpolate(frame, [0, effectiveDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  let scale = 1;
  let translateX = 0;
  let translateY = 0;

  switch (animation) {
    case "zoom-in":
      scale = 1 + progress * 0.15;
      break;
    case "zoom-out":
      scale = 1.15 - progress * 0.15;
      break;
    case "pan-left":
      translateX = interpolate(progress, [0, 1], [35, -35]);
      scale = 1.12;
      break;
    case "pan-right":
      translateX = interpolate(progress, [0, 1], [-35, 35]);
      scale = 1.12;
      break;
    case "ken-burns":
      scale = 1 + progress * 0.18;
      translateX = interpolate(progress, [0, 1], [0, -22]);
      translateY = interpolate(progress, [0, 1], [0, -14]);
      break;
    case "drift-up":
      translateY = interpolate(progress, [0, 1], [22, -22]);
      scale = 1.1;
      break;
    case "drift-down":
      translateY = interpolate(progress, [0, 1], [-22, 22]);
      scale = 1.1;
      break;
    case "parallax":
      translateY = interpolate(progress, [0, 1], [14, -14]);
      translateX = interpolate(progress, [0, 1], [6, -6]);
      scale = 1.12;
      break;
    case "static":
    default:
      scale = 1.02; // tiny scale to avoid edge artifacts
      break;
  }

  return { scale, translateX, translateY };
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export const AnimeScene: React.FC<AnimeSceneProps> = ({
  images,
  cues,
  animation = "ken-burns",
  particles,
  particleColor = "#FFE082",
  particleCount = 20,
  particleIntensity = 0.6,
  backgroundColor = "#0A0A1A",
  vignette = true,
  lightingFrom,
  lightingTo,
  sceneDurationSeconds,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // CRITICAL FIX: useVideoConfig().durationInFrames returns the FULL
  // composition duration (e.g. 930 for a 31s video), NOT the Sequence
  // duration (e.g. 150 for a 5s scene). This caused multi-image crossfade
  // segments to span the wrong range, making images invisible.
  const effectiveDuration = sceneDurationSeconds
    ? Math.round(sceneDurationSeconds * fps)
    : durationInFrames;

  const { scale, translateX, translateY } = useCameraMotion(
    animation,
    effectiveDuration
  );

  const imageCount = images.length;

  // Cross-fade duration in frames (~1.2 seconds)
  const crossfadeDur = Math.round(fps * 1.2);

  /**
   * Compute opacity for image at index `idx`.
   *
   * Single image  → simple spring fade-in, gentle fade-out at end.
   * Multi-image   → each image fades in at its segment start and fades out
   *                  as the next image fades in. Creates a continuous morph
   *                  that simulates subtle motion within the scene.
   */
  // Scene-level fade-in (first 0.5s) and fade-out (last 0.3s)
  const sceneIn = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 80 },
  });
  const sceneOut = interpolate(
    frame,
    [effectiveDuration - 10, effectiveDuration],
    [1, 0.25],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Cue schedule: the incoming image fades in ON TOP of the one it replaces
  // (which stays fully opaque underneath), so a switch never dips to the
  // background the way an opacity cross-dissolve does.
  const cueState =
    cues && cues.length > 0 ? cueLayers(cues, imageCount, frame / fps) : null;

  const getZIndex = (idx: number): number | undefined => {
    if (!cueState) return undefined;
    if (idx === cueState.current) return 2;
    return idx === cueState.previous ? 1 : 0;
  };

  const getOpacity = (idx: number): number => {
    if (cueState) {
      const stack = sceneIn * sceneOut;
      if (idx === cueState.current) {
        return stack * (cueState.previous === null ? 1 : cueState.progress);
      }
      return idx === cueState.previous ? stack : 0;
    }

    if (imageCount <= 1) {
      return sceneIn * sceneOut;
    }

    // Each image owns a time segment; crossfade regions OVERLAP so there's
    // never a gap where both images are at zero opacity.
    //
    // Segment boundaries: [0, segDur, 2*segDur, ...]
    // Image N fades OUT over [segEnd - xfade, segEnd]
    // Image N+1 fades IN  over [segEnd - xfade, segEnd] (same window!)
    //
    // This ensures a smooth blend at every boundary.
    const segmentDur = effectiveDuration / imageCount;
    const segStart = idx * segmentDur;
    const segEnd = segStart + segmentDur;

    // Fade in — first image uses spring, others overlap with prev image's fade-out
    const fadeIn =
      idx === 0
        ? sceneIn
        : interpolate(
            frame,
            [segStart - crossfadeDur, segStart],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

    // Fade out — last image uses scene-level fade; others fade as next blends in
    const fadeOut =
      idx === imageCount - 1
        ? sceneOut
        : interpolate(
            frame,
            [segEnd - crossfadeDur, segEnd],
            [1, 0],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );

    return Math.max(0, Math.min(1, fadeIn * fadeOut));
  };

  // Lighting shift progress
  const lightProgress = interpolate(frame, [0, effectiveDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const lightOpacity =
    lightingFrom && lightingTo
      ? interpolate(lightProgress, [0, 0.3, 0.7, 1], [0, 0.25, 0.25, 0.1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

  return (
    <AbsoluteFill style={{ overflow: "hidden", background: backgroundColor }}>
      {/* Layer 1: Image stack with crossfade + camera motion */}
      {images.map((src, i) => (
        <AbsoluteFill key={i} style={{ zIndex: getZIndex(i) }}>
          <Img
            src={resolveAsset(src)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              opacity: getOpacity(i),
              transform: `scale(${scale}) translate(${translateX}px, ${translateY}px)`,
              willChange: "transform, opacity",
            }}
          />
        </AbsoluteFill>
      ))}

      {/* Layer 2: Animated lighting gradient */}
      {lightingFrom && lightingTo && (
        <AbsoluteFill
          style={{
            background: `linear-gradient(135deg, ${lightingFrom}, ${lightingTo})`,
            opacity: lightOpacity,
            pointerEvents: "none",
          }}
        />
      )}

      {/* Layer 3: Cinematic vignette */}
      {vignette && <AnimeVignette />}

      {/* Layer 4: Particle effects */}
      {particles && (
        <ParticleOverlay
          type={particles}
          count={particleCount}
          color={particleColor}
          intensity={particleIntensity}
        />
      )}
    </AbsoluteFill>
  );
};
