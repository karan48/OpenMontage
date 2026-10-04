import {
  AbsoluteFill,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Word-level caption for TikTok-style highlight display
export interface WordCaption {
  word: string;
  startMs: number;
  endMs: number;
}

interface CaptionOverlayProps {
  words: WordCaption[];
  // How many words to show at once in a "page"
  wordsPerPage?: number;
  fontSize?: number;
  color?: string;
  highlightColor?: string;
  backgroundColor?: string;
  fontFamily?: string;
  /** Distance of the caption box from the bottom edge, as % of frame height.
   *  Unset = 80px (legacy). Shorts: ~22-26 keeps captions above the Shorts UI. */
  bottomPercent?: number;
  /** Start a new page when the gap between two words exceeds this (ms),
   *  e.g. at a speaker change or a silent beat. Unset = fixed-size pages only. */
  breakOnGapMs?: number;
  /** Hide a page this long (ms) after its last word ends instead of holding it
   *  until the next page starts. Unset = hold until the next page (legacy). */
  holdAfterMs?: number;
  /** Start a new page after a word ending a sentence (. ? ! । —). */
  breakAfterSentence?: boolean;
}

interface CaptionPage {
  words: WordCaption[];
  startMs: number;
  endMs: number;
}

function buildPages(words: WordCaption[], wordsPerPage: number, breakOnGapMs?: number, breakAfterSentence?: boolean): CaptionPage[] {
  const pages: CaptionPage[] = [];
  let current: WordCaption[] = [];
  const flush = () => {
    if (current.length === 0) return;
    pages.push({ words: current, startMs: current[0].startMs, endMs: current[current.length - 1].endMs });
    current = [];
  };
  words.forEach((w, i) => {
    const prev = words[i - 1];
    const sentenceEnded = breakAfterSentence && prev && /[.?!।—]$/.test(prev.word.trim());
    if (current.length >= wordsPerPage || sentenceEnded || (breakOnGapMs !== undefined && prev && w.startMs - prev.endMs > breakOnGapMs)) {
      flush();
    }
    current.push(w);
  });
  flush();
  return pages;
}

const PageRenderer: React.FC<{
  page: CaptionPage;
  fontSize: number;
  color: string;
  highlightColor: string;
  backgroundColor: string;
  fontFamily: string;
  paddingBottom: number;
}> = ({ page, fontSize, color, highlightColor, backgroundColor, fontFamily, paddingBottom }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const currentMs = page.startMs + (frame / fps) * 1000;

  // Spring entrance
  const entrance = spring({
    frame,
    fps,
    config: { damping: 18, stiffness: 120 },
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom,
      }}
    >
      <div
        style={{
          opacity: entrance,
          transform: `translateY(${interpolate(entrance, [0, 1], [20, 0])}px)`,
          backgroundColor,
          borderRadius: 12,
          padding: "14px 28px",
          maxWidth: "80%",
          textAlign: "center",
        }}
      >
        <span
          style={{
            fontSize,
            fontWeight: 700,
            fontFamily,
            lineHeight: 1.4,
            whiteSpace: "pre-wrap",
          }}
        >
          {page.words.map((w, i) => {
            const isActive = w.startMs <= currentMs && w.endMs > currentMs;
            const isPast = w.endMs <= currentMs;
            return (
              <span
                key={`${w.startMs}-${i}`}
                style={{
                  color: isActive ? highlightColor : isPast ? color : `${color}99`,
                  transition: "none", // CSS transitions forbidden in Remotion
                  textShadow: isActive
                    ? `0 0 20px ${highlightColor}66, 0 2px 4px rgba(0,0,0,0.5)`
                    : "0 2px 4px rgba(0,0,0,0.5)",
                }}
              >
                {w.word}{i < page.words.length - 1 ? " " : ""}
              </span>
            );
          })}
        </span>
      </div>
    </AbsoluteFill>
  );
};

export const CaptionOverlay: React.FC<CaptionOverlayProps> = ({
  words,
  wordsPerPage = 6,
  fontSize = 42,
  color = "#F8FAFC",
  highlightColor = "#22D3EE",
  backgroundColor = "rgba(15, 23, 42, 0.75)",
  fontFamily = "Space Grotesk, Inter, system-ui, sans-serif",
  bottomPercent,
  breakOnGapMs,
  holdAfterMs,
  breakAfterSentence,
}) => {
  const { fps, height } = useVideoConfig();
  const pages = buildPages(words, wordsPerPage, breakOnGapMs, breakAfterSentence);
  const paddingBottom = bottomPercent !== undefined ? Math.round((height * bottomPercent) / 100) : 80;

  return (
    <AbsoluteFill>
      {pages.map((page, i) => {
        const fromFrame = Math.round((page.startMs / 1000) * fps);
        const nextStart = pages[i + 1]?.startMs ?? page.endMs + 500;
        const endAt = holdAfterMs !== undefined ? Math.min(nextStart, page.endMs + holdAfterMs) : nextStart;
        const duration = Math.max(
          1,
          Math.round(((endAt - page.startMs) / 1000) * fps)
        );

        return (
          <Sequence key={i} from={fromFrame} durationInFrames={duration}>
            <PageRenderer
              page={page}
              fontSize={fontSize}
              color={color}
              highlightColor={highlightColor}
              backgroundColor={backgroundColor}
              fontFamily={fontFamily}
              paddingBottom={paddingBottom}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
