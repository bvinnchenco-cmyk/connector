import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  spring,
  staticFile,
} from "remotion";

export type ConcertPromoProps = {
  artistName: string;
  eventTitle: string;
  date: string;
  city: string;
  venue: string;
  siteUrl: string;
  imageUrl: string;        // hero artist photo
  accentColor: string;     // e.g. "#e63946" for rock, "#7209b7" for pop
  accentColor2: string;    // secondary accent
};

// ── Timing constants (30fps × 15s = 450 frames) ───────────────────────────────
const FPS = 30;
const TOTAL = 450; // 15 seconds

const fadeIn = (frame: number, start: number, duration = 20) =>
  interpolate(frame, [start, start + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });

const slideUp = (frame: number, start: number, duration = 25) =>
  interpolate(frame, [start, start + duration], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

// ── Artist photo hero with Ken Burns zoom ─────────────────────────────────────
const HeroPhoto: React.FC<{ imageUrl: string; frame: number; totalFrames: number }> = ({
  imageUrl,
  frame,
  totalFrames,
}) => {
  const scale = interpolate(frame, [0, totalFrames], [1, 1.08], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ opacity }}>
      <Img
        src={imageUrl}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale})`,
          transformOrigin: "center center",
        }}
      />
      {/* Dark cinematic overlay */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to bottom, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.1) 40%, rgba(0,0,0,0.75) 75%, rgba(0,0,0,0.95) 100%)",
        }}
      />
    </AbsoluteFill>
  );
};

// ── Animated glowing line ──────────────────────────────────────────────────────
const AccentLine: React.FC<{ color: string; frame: number; startFrame: number }> = ({
  color,
  frame,
  startFrame,
}) => {
  const width = interpolate(frame, [startFrame, startFrame + 35], [0, 120], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (
    <div
      style={{
        width: `${width}px`,
        height: 3,
        background: color,
        boxShadow: `0 0 12px ${color}, 0 0 24px ${color}`,
        borderRadius: 2,
        marginBottom: 20,
      }}
    />
  );
};

// ── Main composition ───────────────────────────────────────────────────────────
export const ConcertPromo: React.FC<ConcertPromoProps> = ({
  artistName,
  eventTitle,
  date,
  city,
  venue,
  siteUrl,
  imageUrl,
  accentColor,
  accentColor2,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // Phase timings
  const ARTIST_START = 15;
  const EVENT_START = 55;
  const DATE_START = 90;
  const VENUE_START = 120;
  const URL_START = 330;
  const OUTRO_START = 390;

  // Outro fade
  const outroOpacity = interpolate(
    frame,
    [OUTRO_START, OUTRO_START + 40],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // URL pulse
  const urlPulse = interpolate(
    frame,
    [URL_START, URL_START + 15, URL_START + 30],
    [0.9, 1.05, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ backgroundColor: "#000", fontFamily: "'Arial', sans-serif" }}>
      {/* Hero photo with Ken Burns */}
      <HeroPhoto imageUrl={imageUrl} frame={frame} totalFrames={durationInFrames} />

      {/* Content layer */}
      <AbsoluteFill
        style={{
          opacity: outroOpacity,
          display: "flex",
          flexDirection: "column",
          justifyContent: "flex-end",
          padding: "60px 70px",
        }}
      >
        {/* Accent line */}
        <AccentLine color={accentColor} frame={frame} startFrame={ARTIST_START - 5} />

        {/* Artist name */}
        <div
          style={{
            opacity: fadeIn(frame, ARTIST_START),
            transform: `translateY(${slideUp(frame, ARTIST_START)}px)`,
            fontSize: 88,
            fontWeight: 900,
            color: "#fff",
            letterSpacing: "-2px",
            lineHeight: 1,
            textTransform: "uppercase",
            textShadow: `0 0 60px ${accentColor}55`,
            marginBottom: 16,
          }}
        >
          {artistName}
        </div>

        {/* Event title */}
        <div
          style={{
            opacity: fadeIn(frame, EVENT_START),
            transform: `translateY(${slideUp(frame, EVENT_START)}px)`,
            fontSize: 28,
            fontWeight: 400,
            color: accentColor,
            letterSpacing: "4px",
            textTransform: "uppercase",
            marginBottom: 30,
          }}
        >
          {eventTitle}
        </div>

        {/* Date & City row */}
        <div
          style={{
            opacity: fadeIn(frame, DATE_START),
            transform: `translateY(${slideUp(frame, DATE_START)}px)`,
            display: "flex",
            alignItems: "center",
            gap: 24,
            marginBottom: 12,
          }}
        >
          <div
            style={{
              fontSize: 42,
              fontWeight: 700,
              color: "#fff",
              letterSpacing: "-0.5px",
            }}
          >
            {date}
          </div>
          <div
            style={{
              width: 1,
              height: 40,
              background: "rgba(255,255,255,0.3)",
            }}
          />
          <div
            style={{
              fontSize: 42,
              fontWeight: 700,
              color: "#fff",
            }}
          >
            {city}
          </div>
        </div>

        {/* Venue */}
        <div
          style={{
            opacity: fadeIn(frame, VENUE_START),
            transform: `translateY(${slideUp(frame, VENUE_START)}px)`,
            fontSize: 20,
            fontWeight: 300,
            color: "rgba(255,255,255,0.6)",
            letterSpacing: "2px",
            textTransform: "uppercase",
            marginBottom: 48,
          }}
        >
          {venue}
        </div>

        {/* Site URL — appears late, stays until outro */}
        {frame >= URL_START && (
          <div
            style={{
              opacity: fadeIn(frame, URL_START),
              transform: `scale(${urlPulse})`,
              transformOrigin: "left center",
              display: "inline-flex",
              alignItems: "center",
              gap: 14,
              background: accentColor,
              color: "#fff",
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: "1px",
              padding: "14px 32px",
              borderRadius: 4,
              boxShadow: `0 0 40px ${accentColor}88`,
              width: "fit-content",
            }}
          >
            🎫 {siteUrl}
          </div>
        )}
      </AbsoluteFill>

      {/* Particle/grain overlay for cinematic feel */}
      <AbsoluteFill
        style={{
          background: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E\")",
          opacity: 0.4,
          mixBlendMode: "overlay",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
