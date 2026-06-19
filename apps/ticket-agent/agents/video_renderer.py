"""
Video Renderer Agent — renders a concert promo video via Remotion.

Calls apps/concert-video/render.mjs with concert data,
returns path to the rendered MP4 file.
"""
import os
import json
import subprocess
from pathlib import Path

# Path to the Remotion project (relative to repo root)
REMOTION_DIR = Path(__file__).parent.parent.parent.parent / "apps" / "concert-video"


def render_video(
    concert_info: dict,
    output_path: str | None = None,
    video_format: str = "square",  # "square" | "portrait" | "landscape"
) -> str:
    """
    Renders a 15-second cinematic concert promo video.

    Args:
        concert_info: enriched concert data from researcher
        output_path: where to save the MP4 (auto-generated if None)
        video_format: "square" (1080×1080), "portrait" (1080×1920), "landscape" (1920×1080)

    Returns:
        Absolute path to the rendered MP4 file
    """
    from agents.web_builder import slugify

    artist_slug = slugify(concert_info["artist_name"])

    if output_path is None:
        out_dir = Path("/tmp/concert-videos") / artist_slug
        out_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(out_dir / f"promo-{video_format}.mp4")

    # Build props for Remotion
    image_urls = concert_info.get("image_urls", [])
    props = {
        "artistName": concert_info["artist_name"],
        "eventTitle": concert_info["event_title"],
        "date": concert_info["date"],
        "city": concert_info["city"],
        "venue": concert_info["venue"],
        "siteUrl": concert_info.get("site_url", ""),
        "imageUrl": image_urls[0] if image_urls else "",
        "genre": concert_info.get("genre", ""),
        # accentColor derived from genre inside render.mjs
    }

    _ensure_node_modules()

    env = {**os.environ, "NODE_ENV": "production"}

    result = subprocess.run(
        [
            "node", "render.mjs",
            "--props", json.dumps(props),
            "--output", output_path,
            "--format", video_format,
        ],
        cwd=str(REMOTION_DIR),
        capture_output=True,
        text=True,
        env=env,
        timeout=300,  # 5 min max
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Remotion render failed:\n{result.stderr}\n{result.stdout}"
        )

    # Parse output path from stdout (render.mjs prints "OUTPUT:/path/to/file")
    for line in result.stdout.splitlines():
        if line.startswith("OUTPUT:"):
            return line[7:].strip()

    return output_path


def render_all_formats(concert_info: dict) -> dict[str, str]:
    """
    Renders square + portrait formats in sequence.
    Returns {"square": "/path/square.mp4", "portrait": "/path/portrait.mp4"}
    """
    results = {}
    for fmt in ("square", "portrait"):
        try:
            path = render_video(concert_info, video_format=fmt)
            results[fmt] = path
        except Exception as e:
            results[fmt] = f"ERROR: {e}"
    return results


def _ensure_node_modules():
    """Install npm dependencies if node_modules doesn't exist."""
    node_modules = REMOTION_DIR / "node_modules"
    if not node_modules.exists():
        subprocess.run(
            ["npm", "install"],
            cwd=str(REMOTION_DIR),
            check=True,
            timeout=120,
        )
