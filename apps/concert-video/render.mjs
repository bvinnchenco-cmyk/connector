/**
 * render.mjs — CLI render script called by the Python deployer agent.
 *
 * Usage:
 *   node render.mjs --props '{"artistName":"Coldplay",...}' --output /tmp/out.mp4
 *
 * Or via environment variable:
 *   CONCERT_PROPS='{"artistName":"..."}' OUTPUT_PATH=/tmp/out.mp4 node render.mjs
 */
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import { createRequire } from "module";
import path from "path";
import { fileURLToPath } from "url";
import { parseArgs } from "util";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── Parse args ─────────────────────────────────────────────────────────────────
const { values } = parseArgs({
  args: process.argv.slice(2),
  options: {
    props: { type: "string" },
    output: { type: "string" },
    format: { type: "string" },  // "square" | "portrait" | "landscape"
  },
  strict: false,
});

const propsRaw = values.props || process.env.CONCERT_PROPS;
const outputPath = values.output || process.env.OUTPUT_PATH || "/tmp/concert-promo.mp4";
const format = values.format || process.env.VIDEO_FORMAT || "square";

if (!propsRaw) {
  console.error("Error: --props JSON is required");
  process.exit(1);
}

const inputProps = JSON.parse(propsRaw);

// Video dimensions per format
const FORMATS = {
  square:    { width: 1080, height: 1080 },  // Instagram feed, Threads
  portrait:  { width: 1080, height: 1920 },  // Reels, Stories, TikTok
  landscape: { width: 1920, height: 1080 },  // YouTube, Twitter
};
const { width, height } = FORMATS[format] || FORMATS.square;

// ── Derive accent color from genre ────────────────────────────────────────────
function genreToColors(genre = "") {
  const g = genre.toLowerCase();
  if (g.includes("rock") || g.includes("metal"))
    return { accentColor: "#e63946", accentColor2: "#ff6b35" };
  if (g.includes("pop"))
    return { accentColor: "#7209b7", accentColor2: "#f72585" };
  if (g.includes("electronic") || g.includes("edm") || g.includes("techno"))
    return { accentColor: "#00d4ff", accentColor2: "#7209b7" };
  if (g.includes("hip") || g.includes("rap") || g.includes("r&b"))
    return { accentColor: "#f4a261", accentColor2: "#e76f51" };
  if (g.includes("jazz") || g.includes("soul") || g.includes("blues"))
    return { accentColor: "#e9c46a", accentColor2: "#f4a261" };
  if (g.includes("classical") || g.includes("opera"))
    return { accentColor: "#cdb4db", accentColor2: "#ffc8dd" };
  // Default: electric blue
  return { accentColor: "#00d4ff", accentColor2: "#4cc9f0" };
}

const colors = genreToColors(inputProps.genre);
const finalProps = { ...colors, ...inputProps }; // inputProps can override colors

// ── Render ─────────────────────────────────────────────────────────────────────
console.log(`🎬 Rendering ${format} (${width}×${height}) → ${outputPath}`);
console.log(`   Artist: ${finalProps.artistName}`);

const entryPoint = path.join(__dirname, "src", "index.ts");

try {
  const bundled = await bundle({ entryPoint });

  const composition = await selectComposition({
    serveUrl: bundled,
    id: "ConcertPromo",
    inputProps: finalProps,
  });

  // Override dimensions for the requested format
  composition.width = width;
  composition.height = height;

  await renderMedia({
    composition,
    serveUrl: bundled,
    codec: "h264",
    outputLocation: outputPath,
    inputProps: finalProps,
    logLevel: "warn",
    onProgress: ({ progress }) => {
      process.stdout.write(`\r   Progress: ${Math.round(progress * 100)}%`);
    },
  });

  console.log(`\n✅ Done → ${outputPath}`);
  // Output path on stdout for Python to capture
  process.stdout.write(`\nOUTPUT:${outputPath}\n`);
} catch (err) {
  console.error("❌ Render failed:", err.message);
  process.exit(1);
}
