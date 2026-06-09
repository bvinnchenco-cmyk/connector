"""
Web Builder Agent — generates a modern, designer-quality concert landing page.
"""
import re
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

WEB_BUILDER_SYSTEM = """You are an elite frontend developer and UI designer specializing in concert/music event landing pages.
You create visually stunning, modern, responsive HTML pages with:
- Dark moody concert aesthetic (deep blacks, vibrant accent colors matching the artist)
- Full-screen hero section with artist image and parallax effect
- Smooth animations (CSS keyframes + Intersection Observer)
- Countdown timer to event date
- Artist bio section with glassmorphism cards
- Venue details with embedded map link
- Sticky CTA button "BUY TICKETS"
- Mobile-first responsive design
- Google Fonts integration
- No external JS frameworks — pure HTML/CSS/vanilla JS only

Output ONLY the complete HTML file content, nothing else."""


BUILD_PROMPT = """Create a stunning concert landing page for:

Artist: {artist_name}
Event: {event_title}
Date: {date}
Venue: {venue}, {city}, {country}
Genre: {genre}
Description: {description}
Ticket URL: {ticket_url}
Artist Images: {image_urls}

Requirements:
1. Use the first image as hero background (with dark overlay gradient)
2. Use other images in a gallery/slider section
3. Countdown timer to: {date}
4. "BUY TICKETS" button must link to: {ticket_url}
5. Color palette: derive 2 accent colors from the genre/artist vibe
6. Include Open Graph meta tags for social sharing
7. Page title: "{event_title} — Official Tickets"

Output the complete single-file HTML."""


def build_website(concert_info: dict) -> str:
    """
    Uses Claude to generate a complete concert landing page HTML.
    Returns the HTML string.
    """
    prompt = BUILD_PROMPT.format(
        artist_name=concert_info["artist_name"],
        event_title=concert_info["event_title"],
        date=concert_info["date"],
        venue=concert_info["venue"],
        city=concert_info["city"],
        country=concert_info["country"],
        genre=concert_info["genre"],
        description=concert_info["description"],
        ticket_url=concert_info["ticket_url"],
        image_urls=", ".join(concert_info.get("image_urls", [])[:3])
    )

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8192,
        system=WEB_BUILDER_SYSTEM,
        messages=[{"role": "user", "content": prompt}]
    )

    html = response.content[0].text

    # Strip any markdown code fences if present
    html = re.sub(r'^```html\s*', '', html.strip())
    html = re.sub(r'\s*```$', '', html)

    return html


def save_website(html: str, artist_slug: str, output_dir: str = "/tmp/concert-sites") -> str:
    """Save HTML to disk and return the file path."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    filepath = f"{output_dir}/{artist_slug}/index.html"
    Path(f"{output_dir}/{artist_slug}").mkdir(parents=True, exist_ok=True)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath


def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9-]', '-', name.lower().strip()).strip('-')
