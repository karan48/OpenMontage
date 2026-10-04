import {
  AbsoluteFill,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadFont as loadPoppins } from "@remotion/google-fonts/Poppins";
import { loadFont as loadHind } from "@remotion/google-fonts/Hind";

/**
 * PhoneChat — a generic messenger screen for story beats told through texts
 * (typing… / delete / "is typing" / unsent drafts). Vector UI, so text stays
 * crisp, and Devanagari renders correctly (Poppins + Hind).
 *
 * Deliberately generic: no real app's branding, colours or layout.
 *
 * Layouts:
 *   - "full":  a close-up phone screen (header, a little history, input field
 *              with typed text, keyboard) over a blurred, dimmed backdrop.
 *   - "split": two stacked chat headers whose "typing…" status lines toggle
 *              independently — two people waiting on each other.
 *   - "pill":  a small floating "Name · typing…" pill over a full-bleed image.
 *
 * Steps run sequentially from the start of the scene (see PhoneChatStep).
 * Documented in SCENE_TYPES.md as cut.type "phone_chat".
 */

const { fontFamily: headingFont } = loadPoppins("normal", {
  weights: ["500", "600"],
  subsets: ["latin", "devanagari"],
});
const { fontFamily: bodyFont } = loadHind("normal", {
  weights: ["400", "500"],
  subsets: ["latin", "devanagari"],
});

export type PhoneChatStatus = "typing" | "online" | "none";

export type PhoneChatStep =
  | { kind: "type"; text: string; cps?: number }
  | { kind: "delete"; chars?: number; cps?: number }
  | { kind: "status"; value: PhoneChatStatus }
  | { kind: "send_hover"; seconds?: number }
  | { kind: "counter"; value: number }
  | { kind: "bubble"; side: "in" | "out"; text: string }
  | { kind: "pause"; seconds: number };

export interface PhoneChatBubble {
  side: "in" | "out";
  text: string;
}

export interface PhoneChatLane {
  contactName: string;
  steps: PhoneChatStep[];
  initialStatus?: PhoneChatStatus;
}

export interface PhoneChatProps {
  layout?: "full" | "split" | "pill";
  contactName?: string;
  steps?: PhoneChatStep[];
  initialStatus?: PhoneChatStatus;
  /** Older messages shown faded above the input, for context. */
  history?: PhoneChatBubble[];
  /** split layout: one lane per stacked header (top first). */
  lanes?: PhoneChatLane[];
  backdropImage?: string;
  /** Backdrop blur in px. Defaults: 18 for full/split, 0 for pill. */
  backdropBlur?: number;
  /** Darkening over the backdrop, 0-1. Defaults: 0.55 full/split, 0.15 pill. */
  backdropDim?: number;
  /** Optional story counter shown above the phone, e.g. "Drafts". */
  counterLabel?: string;
  counterStart?: number;
  clockText?: string;
  accentColor?: string;
  backgroundColor?: string;
  /** "none" starts fully on screen (use on the first frame of a video). */
  entrance?: "none" | "rise";
  /** full layout: show an incoming "…" bubble while the contact is typing (default true). */
  typingBubble?: boolean;
  sceneDurationSeconds?: number;
}

// ---------------------------------------------------------------------------
// Palette (anime-drama defaults; overridable through accentColor/backgroundColor)
// ---------------------------------------------------------------------------

const C = {
  bg: "#0E1022",
  surface: "#1C2240",
  surface2: "#262D52",
  text: "#F4F1FA",
  muted: "#A3A8C3",
  inBubble: "#2A3160",
  key: "#2B3156",
};

function resolveAsset(src: string): string {
  if (src.startsWith("http://") || src.startsWith("https://") || src.startsWith("data:")) return src;
  return staticFile(src.replace(/^file:\/\/\/?/, ""));
}

// ---------------------------------------------------------------------------
// Step timeline → state at time t
// ---------------------------------------------------------------------------

interface ChatState {
  text: string;
  status: PhoneChatStatus;
  counter: number | null;
  counterChangedAt: number;
  sendHover: number; // 0-1
  typing: boolean; // a key is being pressed right now
  keySeed: number; // changes per typed/deleted char
  bubbles: { side: "in" | "out"; text: string; at: number }[];
}

function stepDuration(step: PhoneChatStep, textLen: number): number {
  switch (step.kind) {
    case "type":
      return Array.from(step.text).length / (step.cps ?? 12);
    case "delete":
      return (step.chars ?? textLen) / (step.cps ?? 22);
    case "send_hover":
      return step.seconds ?? 1.0;
    case "pause":
      return step.seconds;
    default:
      return 0;
  }
}

function computeState(
  steps: PhoneChatStep[],
  t: number,
  initialStatus: PhoneChatStatus,
  counterStart: number | null,
): ChatState {
  const s: ChatState = {
    text: "",
    status: initialStatus,
    counter: counterStart,
    counterChangedAt: -10,
    sendHover: 0,
    typing: false,
    keySeed: 0,
    bubbles: [],
  };
  let clock = 0;
  for (const step of steps) {
    if (t < clock) break;
    const chars = Array.from(s.text);
    const dur = stepDuration(step, chars.length);
    const local = t - clock;
    const done = local >= dur;
    switch (step.kind) {
      case "type": {
        const add = Array.from(step.text);
        const n = done ? add.length : Math.floor(local * (step.cps ?? 12));
        s.text = chars.concat(add.slice(0, n)).join("");
        s.keySeed += n;
        if (!done) s.typing = true;
        break;
      }
      case "delete": {
        const total = step.chars ?? chars.length;
        const n = done ? total : Math.floor(local * (step.cps ?? 22));
        s.text = chars.slice(0, Math.max(0, chars.length - n)).join("");
        s.keySeed += n;
        if (!done) s.typing = true;
        break;
      }
      case "status":
        s.status = step.value;
        break;
      case "counter":
        s.counter = step.value;
        s.counterChangedAt = clock;
        break;
      case "bubble":
        s.bubbles.push({ side: step.side, text: step.text, at: clock });
        break;
      case "send_hover":
        if (!done) s.sendHover = Math.sin(Math.PI * (local / dur));
        break;
      case "pause":
        break;
    }
    clock += dur;
  }
  return s;
}

// ---------------------------------------------------------------------------
// Small pieces
// ---------------------------------------------------------------------------

const TypingDots: React.FC<{ t: number; color: string; size: number }> = ({ t, color, size }) => (
  <span style={{ display: "inline-flex", gap: size * 0.35, marginLeft: size * 0.3, alignItems: "center" }}>
    {[0, 1, 2].map((i) => {
      const phase = (t * 2.4 - i * 0.18) % 1;
      const lift = Math.max(0, Math.sin(phase * Math.PI * 2));
      return (
        <span
          key={i}
          style={{
            width: size,
            height: size,
            borderRadius: "50%",
            background: color,
            opacity: 0.45 + 0.55 * lift,
            transform: `translateY(${-lift * size * 0.5}px)`,
          }}
        />
      );
    })}
  </span>
);

const StatusLine: React.FC<{ status: PhoneChatStatus; t: number; accent: string; size: number }> = ({
  status,
  t,
  accent,
  size,
}) => {
  if (status === "none") return <div style={{ height: size * 1.3 }} />;
  if (status === "online")
    return (
      <div style={{ fontFamily: bodyFont, fontSize: size, color: C.muted, height: size * 1.3 }}>online</div>
    );
  return (
    <div
      style={{
        fontFamily: bodyFont,
        fontWeight: 500,
        fontSize: size,
        color: accent,
        height: size * 1.3,
        display: "flex",
        alignItems: "center",
      }}
    >
      typing
      <TypingDots t={t} color={accent} size={size * 0.28} />
    </div>
  );
};

const Avatar: React.FC<{ name: string; size: number; accent: string }> = ({ name, size, accent }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: "50%",
      background: `linear-gradient(135deg, ${accent}, #5B6CFF)`,
      color: C.bg,
      fontFamily: headingFont,
      fontWeight: 600,
      fontSize: size * 0.46,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
    }}
  >
    {Array.from(name.trim())[0]?.toUpperCase() ?? "?"}
  </div>
);

const Backdrop: React.FC<{ src?: string; blur: number; dim: number; bg: string; t: number; dur: number }> = ({
  src,
  blur,
  dim,
  bg,
  t,
  dur,
}) => {
  const scale = interpolate(t, [0, Math.max(dur, 0.1)], [1.08, 1.13], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: bg }}>
      {src && (
        <Img
          src={resolveAsset(src)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: blur > 0 ? `blur(${blur}px)` : undefined,
            transform: `scale(${scale})`,
          }}
        />
      )}
      <AbsoluteFill style={{ background: `rgba(14,16,34,${dim})` }} />
    </AbsoluteFill>
  );
};

const KEY_ROWS = ["qwertyuiop", "asdfghjkl", "zxcvbnm"];

const Keyboard: React.FC<{ width: number; pressedSeed: number; typing: boolean; accent: string }> = ({
  width,
  pressedSeed,
  typing,
  accent,
}) => {
  const keyW = (width - 11 * 10) / 10;
  const pressedIndex = typing ? (pressedSeed * 7 + 3) % 26 : -1;
  let idx = 0;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 14, padding: "18px 10px 10px", background: C.surface }}>
      {KEY_ROWS.map((row) => (
        <div key={row} style={{ display: "flex", justifyContent: "center", gap: 10 }}>
          {Array.from(row).map((ch) => {
            const pressed = idx++ === pressedIndex;
            return (
              <div
                key={ch}
                style={{
                  width: keyW,
                  height: keyW * 1.25,
                  borderRadius: 10,
                  background: pressed ? accent : C.key,
                  color: pressed ? C.bg : C.muted,
                  fontFamily: bodyFont,
                  fontSize: keyW * 0.5,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transform: pressed ? "translateY(-4px) scale(1.08)" : undefined,
                }}
              >
                {ch}
              </div>
            );
          })}
        </div>
      ))}
      <div style={{ display: "flex", justifyContent: "center" }}>
        <div style={{ width: width * 0.5, height: keyW * 1.1, borderRadius: 10, background: C.key }} />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Layouts
// ---------------------------------------------------------------------------

const FullLayout: React.FC<{
  props: PhoneChatProps;
  state: ChatState;
  t: number;
  accent: string;
  W: number;
  H: number;
}> = ({ props, state, t, accent, W, H }) => {
  const screenW = W * 0.8;
  const screenH = H * 0.53;
  // Kept below the Shorts top bar; the bottom stays above the caption band.
  const top = H * 0.11;
  const showCaret = state.typing || Math.floor(t * 2) % 2 === 0;
  const empty = state.text.length === 0;
  const counterPop =
    state.counter !== null ? interpolate(t - state.counterChangedAt, [0, 0.12, 0.3], [1, 1.18, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 1;

  return (
    <>
      {props.counterLabel && state.counter !== null && (
        <div
          style={{
            position: "absolute",
            top: top - 84,
            left: 0,
            right: 0,
            display: "flex",
            justifyContent: "center",
          }}
        >
          <div
            style={{
              fontFamily: headingFont,
              fontWeight: 600,
              fontSize: 34,
              color: C.text,
              background: C.surface,
              border: `2px solid ${accent}`,
              borderRadius: 999,
              padding: "8px 26px",
              transform: `scale(${counterPop})`,
              boxShadow: "0 6px 24px rgba(0,0,0,0.4)",
            }}
          >
            {props.counterLabel}: <span style={{ color: accent }}>{state.counter}</span>
          </div>
        </div>
      )}
      <div
        style={{
          position: "absolute",
          top,
          left: (W - screenW) / 2,
          width: screenW,
          height: screenH,
          borderRadius: 54,
          border: "12px solid #05060F",
          background: C.bg,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          boxShadow: `0 30px 90px rgba(0,0,0,0.55), 0 0 120px rgba(91,108,255,0.25)`,
        }}
      >
        {/* status bar */}
        <div style={{ display: "flex", justifyContent: "space-between", padding: "18px 36px 4px", fontFamily: bodyFont, fontSize: 26, color: C.muted }}>
          <span>{props.clockText ?? "11:42"}</span>
          <span style={{ letterSpacing: 3 }}>▮▮▮ ◔</span>
        </div>
        {/* header */}
        <div style={{ display: "flex", alignItems: "center", gap: 22, padding: "14px 30px 20px", borderBottom: `1px solid ${C.surface2}` }}>
          <span style={{ fontFamily: headingFont, fontSize: 44, color: C.muted, marginRight: 4 }}>‹</span>
          <Avatar name={props.contactName ?? "?"} size={84} accent={accent} />
          <div style={{ display: "flex", flexDirection: "column" }}>
            <div style={{ fontFamily: headingFont, fontWeight: 600, fontSize: 42, color: C.text, lineHeight: 1.2 }}>{props.contactName}</div>
            <StatusLine status={state.status} t={t} accent={accent} size={28} />
          </div>
        </div>
        {/* history + bubbles */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 14, padding: "18px 28px" }}>
          {(props.history ?? []).map((b, i) => (
            <Bubble key={`h${i}`} side={b.side} text={b.text} opacity={0.55} accent={accent} />
          ))}
          {state.bubbles.map((b, i) => (
            <Bubble key={`b${i}`} side={b.side} text={b.text} opacity={interpolate(t - b.at, [0, 0.2], [0, 1], { extrapolateRight: "clamp" })} accent={accent} />
          ))}
          {(props.typingBubble ?? true) && state.status === "typing" && (
            <div style={{ display: "flex", justifyContent: "flex-start" }}>
              <div
                style={{
                  padding: "22px 30px",
                  borderRadius: 34,
                  borderBottomLeftRadius: 8,
                  background: C.inBubble,
                  border: `1px solid ${accent}55`,
                  boxShadow: `0 0 28px ${accent}33`,
                  display: "flex",
                  alignItems: "center",
                }}
              >
                <TypingDots t={t} color={accent} size={18} />
              </div>
            </div>
          )}
        </div>
        {/* input row */}
        <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "14px 22px 18px" }}>
          <div
            style={{
              flex: 1,
              minHeight: 92,
              borderRadius: 46,
              background: C.surface2,
              display: "flex",
              alignItems: "center",
              padding: "10px 32px",
              fontFamily: bodyFont,
              fontSize: 46,
              color: empty ? C.muted : C.text,
            }}
          >
            {empty ? (
              <>
                <span style={{ opacity: showCaret ? 1 : 0, color: accent, marginRight: 4 }}>|</span>
                <span style={{ opacity: 0.6 }}>Message</span>
              </>
            ) : (
              <span>
                {state.text}
                <span style={{ opacity: showCaret ? 1 : 0, color: accent, marginLeft: 2 }}>|</span>
              </span>
            )}
          </div>
          <div style={{ position: "relative", width: 92, height: 92 }}>
            <div
              style={{
                position: "absolute",
                inset: -18 * state.sendHover,
                borderRadius: "50%",
                border: `4px solid ${accent}`,
                opacity: 0.7 * state.sendHover,
              }}
            />
            <div
              style={{
                width: 92,
                height: 92,
                borderRadius: "50%",
                background: empty ? C.surface2 : accent,
                color: empty ? C.muted : C.bg,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: headingFont,
                fontSize: 44,
                fontWeight: 600,
              }}
            >
              {empty ? "●" : "➤"}
            </div>
            {/* thumb shadow hovering over Send */}
            <div
              style={{
                position: "absolute",
                left: -40,
                top: 30 - 30 * state.sendHover,
                width: 170,
                height: 220,
                borderRadius: "50%",
                background: "radial-gradient(closest-side, rgba(0,0,0,0.55), rgba(0,0,0,0))",
                opacity: state.sendHover,
              }}
            />
          </div>
        </div>
        <Keyboard width={screenW - 24} pressedSeed={state.keySeed} typing={state.typing} accent={accent} />
      </div>
    </>
  );
};

const Bubble: React.FC<{ side: "in" | "out"; text: string; opacity: number; accent: string }> = ({ side, text, opacity, accent }) => (
  <div style={{ display: "flex", justifyContent: side === "out" ? "flex-end" : "flex-start", opacity }}>
    <div
      style={{
        maxWidth: "78%",
        padding: "14px 24px",
        borderRadius: 30,
        borderBottomRightRadius: side === "out" ? 8 : 30,
        borderBottomLeftRadius: side === "in" ? 8 : 30,
        background: side === "out" ? `${accent}33` : C.inBubble,
        border: side === "out" ? `1px solid ${accent}66` : "none",
        fontFamily: bodyFont,
        fontSize: 34,
        color: C.text,
        lineHeight: 1.35,
      }}
    >
      {text}
    </div>
  </div>
);

const SplitLayout: React.FC<{ lanes: PhoneChatLane[]; t: number; accent: string; W: number; H: number }> = ({ lanes, t, accent, W, H }) => {
  const cardW = W * 0.8;
  const cardH = 230;
  const gap = 90;
  const total = lanes.length * cardH + (lanes.length - 1) * gap;
  const top = H * 0.36 - total / 2;
  return (
    <>
      {lanes.map((lane, i) => {
        const st = computeState(lane.steps, t, lane.initialStatus ?? "online", null);
        const active = st.status === "typing";
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: top + i * (cardH + gap),
              left: (W - cardW) / 2,
              width: cardW,
              height: cardH,
              borderRadius: 40,
              background: C.surface,
              border: `2px solid ${active ? accent : C.surface2}`,
              boxShadow: active ? `0 0 60px ${accent}55` : "0 12px 40px rgba(0,0,0,0.45)",
              display: "flex",
              alignItems: "center",
              gap: 30,
              padding: "0 44px",
            }}
          >
            <Avatar name={lane.contactName} size={120} accent={accent} />
            <div>
              <div style={{ fontFamily: headingFont, fontWeight: 600, fontSize: 52, color: C.text }}>{lane.contactName}</div>
              <StatusLine status={st.status} t={t} accent={accent} size={38} />
            </div>
          </div>
        );
      })}
    </>
  );
};

const PillLayout: React.FC<{ name: string; state: ChatState; t: number; accent: string; W: number; H: number }> = ({ name, state, t, accent, W, H }) => {
  if (state.status === "none") return null;
  return (
    <div style={{ position: "absolute", top: H * 0.12, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          padding: "14px 34px 14px 16px",
          borderRadius: 999,
          background: "rgba(28,34,64,0.88)",
          border: `2px solid ${accent}88`,
          boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
        }}
      >
        <Avatar name={name} size={64} accent={accent} />
        <span style={{ fontFamily: headingFont, fontWeight: 600, fontSize: 38, color: C.text }}>{name}</span>
        <span style={{ color: C.muted, fontSize: 34 }}>·</span>
        <StatusLine status={state.status} t={t} accent={accent} size={34} />
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

export const PhoneChat: React.FC<PhoneChatProps> = (props) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const t = frame / fps;
  const layout = props.layout ?? "full";
  const accent = props.accentColor ?? "#FF8FA3";
  const dur = props.sceneDurationSeconds ?? 4;
  const state = computeState(props.steps ?? [], t, props.initialStatus ?? "online", props.counterStart ?? null);

  const enter =
    props.entrance === "none"
      ? 1
      : spring({ frame, fps, config: { damping: 200, stiffness: 120, mass: 0.6 }, durationInFrames: Math.round(0.35 * fps) });
  const content =
    layout === "split" ? (
      <SplitLayout lanes={props.lanes ?? []} t={t} accent={accent} W={W} H={H} />
    ) : layout === "pill" ? (
      <PillLayout name={props.contactName ?? ""} state={state} t={t} accent={accent} W={W} H={H} />
    ) : (
      <FullLayout props={props} state={state} t={t} accent={accent} W={W} H={H} />
    );

  return (
    <AbsoluteFill>
      <Backdrop
        src={props.backdropImage}
        blur={props.backdropBlur ?? (layout === "pill" ? 0 : 18)}
        dim={props.backdropDim ?? (layout === "pill" ? 0.15 : 0.55)}
        bg={props.backgroundColor ?? C.bg}
        t={t}
        dur={dur}
      />
      <AbsoluteFill
        style={{
          opacity: enter,
          transform: `translateY(${(1 - enter) * 40}px) scale(${0.97 + 0.03 * enter})`,
        }}
      >
        {content}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
