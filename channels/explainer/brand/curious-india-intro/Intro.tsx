import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";

/**
 * Curious India channel intro — 3.0 s, locked brand asset.
 *
 *  0.00 s  ink-black field; a saffron hairline (left) and a green hairline (right) draw in toward the centre
 *  0.13 s  the badge iris-reveals from the centre while it settles 0.92 -> 1.00
 *  1.00 s  the bulb glows once (pairs with the sting's bell)
 *  1.50 s  a soft light sweep crosses the badge; a slow 3% push-in runs underneath
 *  2.70 s  fade to black; the video cuts back in at 3.00 s
 *
 * The badge is shown at its NATIVE size (logo_circle.png is 584 px; the source logo is only 600 px) and is never
 * scaled above 1.03, so it stays sharp at 1080p.
 */
export const INTRO_FRAMES = 90;

const W = 1920;
const H = 1080;
const CX = W / 2;
const CY = H / 2;
const BADGE = 584; // native size of logo_circle.png
const R = 292; // radius of the circle inside logo_circle.png
const BULB = { x: 385 - 292, y: 98 - 292 }; // bulb centre relative to the badge centre, native px
const SAFFRON = "#FF9933";
const GREEN = "#138808";

const ease = (
  f: number,
  a: number,
  b: number,
  from = 0,
  to = 1,
  easing: (t: number) => number = Easing.out(Easing.cubic),
) =>
  interpolate(f, [a, b], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing,
  });

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();

  // hairlines
  const lineT = ease(frame, 0, 10);
  const lineFade = ease(frame, 64, 80, 1, 0, Easing.inOut(Easing.quad));

  // badge
  const settle = ease(frame, 4, 24, 0.92, 1.0);
  const push = interpolate(frame, [24, 86], [1.0, 1.03], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const s = settle * push;
  const iris = ease(frame, 4, 22, 0, R + 4);
  const badgeOpacity = ease(frame, 4, 12);

  // ambient tricolour glow behind the badge
  const ambient = ease(frame, 4, 26);

  // bulb pulse (frames 30 -> 50, peak at 36)
  const pulse = interpolate(frame, [30, 36, 50], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pulseScale = ease(frame, 30, 50, 0.55, 1.35);

  // light sweep (frames 46 -> 66)
  const sweepX = ease(frame, 46, 66, -460, 520, Easing.inOut(Easing.quad));
  const sweepOn = interpolate(frame, [46, 52, 62, 66], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // fade out
  const out = ease(frame, 82, 89, 1, 0, Easing.in(Easing.quad));

  const bulbX = CX + BULB.x * s;
  const bulbY = CY + BULB.y * s;

  return (
    <AbsoluteFill
      style={{
        background: "radial-gradient(ellipse at 50% 50%, #0E1826 0%, #070C14 55%, #03060A 100%)",
      }}
    >
      <AbsoluteFill style={{ opacity: out }}>
        {/* ambient glows: saffron on the left, green on the right (echo the logo's two arcs) */}
        <div
          style={{
            position: "absolute",
            left: CX - 200 - 260,
            top: CY - 260,
            width: 520,
            height: 520,
            borderRadius: "50%",
            background: SAFFRON,
            opacity: 0.2 * ambient,
            filter: "blur(90px)",
          }}
        />
        <div
          style={{
            position: "absolute",
            left: CX + 200 - 260,
            top: CY - 260,
            width: 520,
            height: 520,
            borderRadius: "50%",
            background: GREEN,
            opacity: 0.18 * ambient,
            filter: "blur(90px)",
          }}
        />

        {/* hairlines */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: CY - 1.5,
            width: CX * lineT,
            height: 3,
            background: `linear-gradient(90deg, rgba(255,153,51,0) 0%, ${SAFFRON} 60%, ${SAFFRON} 100%)`,
            opacity: lineFade,
          }}
        />
        <div
          style={{
            position: "absolute",
            right: 0,
            top: CY - 1.5,
            width: CX * lineT,
            height: 3,
            background: `linear-gradient(270deg, rgba(19,136,8,0) 0%, ${GREEN} 60%, ${GREEN} 100%)`,
            opacity: lineFade,
          }}
        />

        {/* the badge: iris reveal + settle + slow push-in */}
        <div
          style={{
            position: "absolute",
            left: CX - BADGE / 2,
            top: CY - BADGE / 2,
            width: BADGE,
            height: BADGE,
            transform: `scale(${s})`,
            transformOrigin: "50% 50%",
            opacity: badgeOpacity,
            clipPath: `circle(${iris}px at 50% 50%)`,
          }}
        >
          <Img src={staticFile("logo_circle.png")} style={{ width: BADGE, height: BADGE, display: "block" }} />
          {/* light sweep, clipped to the badge circle */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              clipPath: `circle(${R}px at 50% 50%)`,
              mixBlendMode: "screen",
              opacity: sweepOn,
            }}
          >
            <div
              style={{
                position: "absolute",
                left: BADGE / 2 + sweepX - 80,
                top: -160,
                width: 160,
                height: BADGE + 320,
                transform: "rotate(18deg)",
                background:
                  "linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.20) 50%, rgba(255,255,255,0) 100%)",
              }}
            />
          </div>
        </div>

        {/* bulb glow (screen blend) */}
        <div
          style={{
            position: "absolute",
            left: bulbX - 170,
            top: bulbY - 170,
            width: 340,
            height: 340,
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(255,214,102,0.95) 0%, rgba(255,200,69,0.38) 32%, rgba(255,200,69,0) 68%)",
            mixBlendMode: "screen",
            opacity: pulse * badgeOpacity,
            transform: `scale(${pulseScale})`,
          }}
        />
      </AbsoluteFill>

      {/* fine grain to keep the dark gradient from banding in H.264 */}
      <AbsoluteFill style={{ opacity: 0.05, mixBlendMode: "overlay" }}>
        <svg width={W} height={H}>
          <filter id="grain">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 7} stitchTiles="stitch" />
          </filter>
          <rect width={W} height={H} filter="url(#grain)" />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
