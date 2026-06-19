"""
Web Builder Agent — generates a modern, designer-quality concert landing page.

Two-step approach:
  1. Prompt Architect (Claude Opus) builds a detailed, event-specific design brief
  2. Site Builder (Claude Opus) turns that brief into a complete single-file HTML page
"""
import re
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

# ── Step 1: Prompt Architect ───────────────────────────────────────────────────

PROMPT_ARCHITECT_SYSTEM = """You are a creative director specialising in concert event marketing.
Your job is to write a detailed design brief for a web developer who will build a concert landing page.

The brief must always include these MANDATORY BLOCKS — they appear on every site but adapted to the event:
1. DISCOUNT BADGE — "{discount}% скидка" shown prominently near the CTA button
2. ARTIST PHOTO — hero full-screen image with cinematic dark overlay
3. LOCATION — venue + city in VERY LARGE typography (min 4rem), impossible to miss
4. DATE & TIME — displayed in VERY LARGE bold font, countdown timer below it
5. ATMOSPHERE BLOCK — 3-4 sentences evoking the emotional experience: crowd energy,
   lights, sound, what it FEELS like to be there. Must make the visitor want to buy NOW.
6. SOCIAL PROOF — "X тысяч фанатов уже купили билеты" style line (invent a plausible number)
7. BUY TICKETS CTA — sticky button always visible, links to the ticket URL

Beyond the mandatory blocks, tailor everything else to the specific event:
- Color palette derived from artist genre and vibe
- Font choices matching the mood
- Unique section ideas specific to this artist/event
- Suggested animations and micro-interactions

Output a detailed design brief in Russian, structured with clear sections."""


PROMPT_ARCHITECT_USER = """Write a design brief for this concert event:

Артист: {artist_name}
Событие: {event_title}
Дата: {date}
Место: {venue}, {city}, {country}
Жанр: {genre}
Описание: {description}
Скидка: {discount}%
URL билетов: {ticket_url}
Фото артиста: {image_urls}
Дополнительный контекст из интернета: {web_context}

Create a detailed, inspiring design brief that will result in a world-class concert landing page."""


# ── Step 2: Site Builder ───────────────────────────────────────────────────────

SITE_BUILDER_SYSTEM = """You are an elite frontend developer. You write stunning, complete single-file HTML pages.

Technical rules:
- Pure HTML + CSS + vanilla JS only (no React, no Vue, no external frameworks)
- Google Fonts via <link> in <head> is allowed
- All CSS in <style> tag, all JS in <script> tag at bottom of body
- Mobile-first responsive design
- Page must work perfectly when opened as a local file (no build step needed)
- Output ONLY the raw HTML — no markdown, no code fences, no explanation

Design rules:
- Follow the design brief EXACTLY
- Every MANDATORY BLOCK from the brief must be implemented
- Dark concert aesthetic by default
- Smooth CSS animations (keyframes + Intersection Observer for scroll reveals)
- Countdown timer using vanilla JS (updates every second)
- Sticky "КУПИТЬ БИЛЕТЫ" button always visible on mobile and desktop
- Open Graph meta tags for social sharing
- Lazy-load images with fade-in effect"""


SITE_BUILDER_USER = """Build the concert landing page according to this design brief:

{design_brief}

CRITICAL REMINDERS:
- Discount badge: {discount}% must be visible near the buy button
- Ticket URL for ALL buttons/links: {ticket_url}
- Artist images to use: {image_urls}
- Page language: RUSSIAN
- Output raw HTML only, starting with <!DOCTYPE html>"""


# ── Public API ─────────────────────────────────────────────────────────────────

def build_website(concert_info: dict) -> str:
    """
    Two-step pipeline: design brief → HTML page.
    Returns the complete HTML string.
    """
    discount = concert_info.get("discount", 15)
    image_urls = concert_info.get("image_urls", [])
    image_list = "\n".join(f"- {u}" for u in image_urls[:5]) if image_urls else "нет (использовать тёмный градиентный фон)"

    # Step 1 — generate design brief
    brief_response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=3000,
        system=PROMPT_ARCHITECT_SYSTEM,
        messages=[{
            "role": "user",
            "content": PROMPT_ARCHITECT_USER.format(
                artist_name=concert_info["artist_name"],
                event_title=concert_info["event_title"],
                date=concert_info["date"],
                venue=concert_info["venue"],
                city=concert_info["city"],
                country=concert_info["country"],
                genre=concert_info["genre"],
                description=concert_info["description"],
                discount=discount,
                ticket_url=concert_info["ticket_url"],
                image_urls=image_list,
                web_context=concert_info.get("web_context", "нет дополнительного контекста")
            )
        }]
    )
    design_brief = brief_response.content[0].text

    # Step 2 — build HTML from brief
    html_response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8192,
        system=SITE_BUILDER_SYSTEM,
        messages=[{
            "role": "user",
            "content": SITE_BUILDER_USER.format(
                design_brief=design_brief,
                discount=discount,
                ticket_url=concert_info["ticket_url"],
                image_urls=image_list
            )
        }]
    )

    html = html_response.content[0].text
    html = re.sub(r'^```html\s*', '', html.strip())
    html = re.sub(r'\s*```$', '', html)

    return html


def save_website(html: str, artist_slug: str, output_dir: str = "/tmp/concert-sites") -> str:
    """Save HTML to disk and return the file path."""
    site_dir = Path(output_dir) / artist_slug
    site_dir.mkdir(parents=True, exist_ok=True)
    filepath = site_dir / "index.html"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return str(filepath)


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    return re.sub(r'-+', '-', slug).strip('-')
