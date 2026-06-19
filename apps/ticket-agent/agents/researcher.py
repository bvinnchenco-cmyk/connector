"""
Research Agent — collects artist/concert info and real photos via web APIs.

Image sources (in priority order):
  1. Wikipedia API          — free, no key, official press photos
  2. Last.fm API            — free key, artist images
  3. Brave Search API       — paid, best quality (optional)
  4. DuckDuckGo scrape      — fallback, no key needed
"""
import os
import re
import json
import asyncio
import httpx
import urllib.parse
from typing import TypedDict
import anthropic

client = anthropic.Anthropic()

HEADERS = {"User-Agent": "ConcertTicketAgent/1.0 (contact@yourdomain.com)"}


# ── Image fetchers ─────────────────────────────────────────────────────────────

async def _images_from_wikipedia(artist_name: str) -> list[str]:
    """Fetch artist images from Wikipedia. Free, no key needed."""
    urls = []
    try:
        async with httpx.AsyncClient(timeout=10, headers=HEADERS) as http:
            # Step 1: find the Wikipedia page title
            search_resp = await http.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query", "list": "search",
                    "srsearch": artist_name, "srlimit": 1,
                    "format": "json"
                }
            )
            results = search_resp.json().get("query", {}).get("search", [])
            if not results:
                return []

            title = results[0]["title"]

            # Step 2: get images on that page
            img_resp = await http.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query", "titles": title,
                    "prop": "images", "imlimit": 10,
                    "format": "json"
                }
            )
            pages = img_resp.json().get("query", {}).get("pages", {})
            image_names = []
            for page in pages.values():
                for img in page.get("images", []):
                    name = img["title"]
                    # Skip icons, flags, logos — keep photos
                    if any(skip in name.lower() for skip in ["flag", "logo", "icon", "map", "svg"]):
                        continue
                    image_names.append(name)

            # Step 3: resolve image names to direct URLs
            if image_names:
                titles_param = "|".join(image_names[:5])
                info_resp = await http.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query", "titles": titles_param,
                        "prop": "imageinfo", "iiprop": "url",
                        "iiurlwidth": 1200, "format": "json"
                    }
                )
                for page in info_resp.json().get("query", {}).get("pages", {}).values():
                    for ii in page.get("imageinfo", []):
                        url = ii.get("thumburl") or ii.get("url")
                        if url:
                            urls.append(url)
    except Exception:
        pass
    return urls


async def _images_from_lastfm(artist_name: str) -> list[str]:
    """Fetch artist images from Last.fm API. Requires LASTFM_API_KEY."""
    api_key = os.environ.get("LASTFM_API_KEY")
    if not api_key:
        return []
    urls = []
    try:
        async with httpx.AsyncClient(timeout=10, headers=HEADERS) as http:
            resp = await http.get(
                "https://ws.audioscrobbler.com/2.0/",
                params={
                    "method": "artist.getinfo",
                    "artist": artist_name,
                    "api_key": api_key,
                    "format": "json"
                }
            )
            data = resp.json()
            images = data.get("artist", {}).get("image", [])
            for img in images:
                url = img.get("#text", "")
                size = img.get("size", "")
                if url and size in ("extralarge", "mega", "large"):
                    urls.append(url)
    except Exception:
        pass
    return urls


async def _images_from_brave(artist_name: str) -> list[str]:
    """Fetch artist images via Brave Search Images API. Requires BRAVE_API_KEY."""
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return []
    urls = []
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(
                "https://api.search.brave.com/res/v1/images/search",
                params={
                    "q": f"{artist_name} official press photo concert",
                    "count": 5,
                    "safesearch": "moderate"
                },
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key
                }
            )
            for result in resp.json().get("results", []):
                url = result.get("properties", {}).get("url")
                if url:
                    urls.append(url)
    except Exception:
        pass
    return urls


async def _images_from_duckduckgo(artist_name: str) -> list[str]:
    """Scrape DuckDuckGo image search as last-resort fallback."""
    urls = []
    try:
        query = urllib.parse.quote(f"{artist_name} official press photo")
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=HEADERS) as http:
            # Get vqd token
            resp = await http.get(f"https://duckduckgo.com/?q={query}&iax=images&ia=images")
            vqd_match = re.search(r"vqd=['\"]([\d-]+)['\"]", resp.text)
            if not vqd_match:
                return []
            vqd = vqd_match.group(1)

            img_resp = await http.get(
                "https://duckduckgo.com/i.js",
                params={"q": f"{artist_name} official press photo", "vqd": vqd, "f": ",,,,,", "p": "1"},
                headers={**HEADERS, "Referer": "https://duckduckgo.com/"}
            )
            for result in img_resp.json().get("results", [])[:5]:
                url = result.get("image")
                if url:
                    urls.append(url)
    except Exception:
        pass
    return urls


async def fetch_artist_images(artist_name: str) -> list[str]:
    """
    Tries all image sources in priority order, returns up to 5 unique URLs.
    """
    # Run all sources in parallel
    results = await asyncio.gather(
        _images_from_wikipedia(artist_name),
        _images_from_lastfm(artist_name),
        _images_from_brave(artist_name),
        _images_from_duckduckgo(artist_name),
        return_exceptions=True
    )

    seen = set()
    urls = []
    for source in results:
        if isinstance(source, list):
            for url in source:
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)
        if len(urls) >= 5:
            break

    return urls[:5]


# ── Web search (text) ──────────────────────────────────────────────────────────

async def _search_brave_text(query: str) -> str:
    """Text search via Brave Search API."""
    api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=10) as http:
            resp = await http.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key
                }
            )
            snippets = []
            for r in resp.json().get("web", {}).get("results", []):
                snippets.append(f"{r.get('title','')}: {r.get('description','')}")
            return "\n".join(snippets)
    except Exception:
        return ""


async def fetch_page(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True, headers=HEADERS) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            # Strip HTML tags for cleaner text
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text)
            return text[:6000]
    except Exception as e:
        return f"Error: {e}"


# ── Research prompt ────────────────────────────────────────────────────────────

RESEARCH_PROMPT = """You are a concert research assistant. Given a raw event description and ticket URL,
extract and enrich the following structured information.

Use web search to find:
1. Artist biography and genre
2. Concert/tour details (date, venue, city)
3. Notable recent achievements, albums, tours
4. What the live show is known for (pyrotechnics, crowd energy, stage design, etc.)

Return ONLY valid JSON matching this schema:
{
  "artist_name": "string",
  "event_title": "string",
  "date": "string (human readable in Russian, e.g. '15 июня 2025')",
  "venue": "string",
  "city": "string",
  "country": "string",
  "description": "string (3-4 sentences in Russian, exciting emotional tone)",
  "genre": "string",
  "web_context": "string (key facts: career highlights, live show reputation, fan base size, recent albums)",
  "discount": number (extract from input if mentioned, default 15),
  "ticket_url": "string"
}"""


# ── Main research function ─────────────────────────────────────────────────────

def research_concert(raw_input: str, ticket_url: str) -> dict:
    """
    Researches a concert event and returns enriched ConcertInfo with real image URLs.
    """
    tools = [
        {
            "name": "web_search",
            "description": "Search the web for text information about an artist or concert event",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch_url",
            "description": "Fetch and read the text content of a webpage",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"}
                },
                "required": ["url"]
            }
        }
    ]

    messages = [{
        "role": "user",
        "content": f"Research this concert and return structured JSON:\n\nEvent: {raw_input}\nTicket URL: {ticket_url}\n\n{RESEARCH_PROMPT}"
    }]

    # Agentic loop — Claude searches for text info
    data = None
    for _ in range(8):
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=4096,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    match = re.search(r'\{.*\}', block.text, re.DOTALL)
                    if match:
                        data = json.loads(match.group())
                        break
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "web_search":
                        result = asyncio.run(_search_brave_text(block.input["query"]))
                        if not result:
                            result = f"[No BRAVE_API_KEY set — configure it in .env for real search results]"
                    elif block.name == "fetch_url":
                        result = asyncio.run(fetch_page(block.input["url"]))
                    else:
                        result = "Tool not available"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

    # Fallback if agentic loop produced nothing
    if not data:
        fallback = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": f"Parse this concert info and return JSON:\n{raw_input}\nTicket URL: {ticket_url}\n\n{RESEARCH_PROMPT}"
            }]
        )
        match = re.search(r'\{.*\}', fallback.content[0].text, re.DOTALL)
        if match:
            data = json.loads(match.group())

    if not data:
        raise ValueError("Could not extract concert info")

    data["ticket_url"] = ticket_url
    data.setdefault("discount", 15)

    # Fetch real artist photos in parallel with image sources
    artist_name = data.get("artist_name", raw_input.split()[0])
    image_urls = asyncio.run(fetch_artist_images(artist_name))
    data["image_urls"] = image_urls

    return data
