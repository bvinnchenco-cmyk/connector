"""
Research Agent — collects artist/concert info and images via web search.
"""
import httpx
import asyncio
import re
from typing import TypedDict
import anthropic

client = anthropic.Anthropic()


class ConcertInfo(TypedDict):
    artist_name: str
    event_title: str
    date: str
    venue: str
    city: str
    country: str
    description: str
    genre: str
    image_urls: list[str]
    ticket_url: str


RESEARCH_PROMPT = """You are a concert research assistant. Given a raw event description and ticket URL,
extract and enrich the following structured information.

Use web search to find:
1. Artist biography and genre
2. Concert/tour details (date, venue, city)
3. High-quality official images of the artist (from official sites, press kits)
4. Any notable recent achievements or albums

Return ONLY valid JSON matching this schema:
{
  "artist_name": "string",
  "event_title": "string",
  "date": "string (human readable, e.g. 'June 15, 2025')",
  "venue": "string",
  "city": "string",
  "country": "string",
  "description": "string (2-3 sentences, exciting tone)",
  "genre": "string",
  "image_urls": ["url1", "url2", "url3"],
  "ticket_url": "string"
}"""


async def fetch_page(url: str) -> str:
    """Fetch text content from a URL."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as http:
            resp = await http.get(url, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            return resp.text[:8000]
    except Exception as e:
        return f"Error fetching {url}: {e}"


async def search_artist_images(artist_name: str) -> list[str]:
    """Search for artist images using DuckDuckGo image search."""
    query = f"{artist_name} concert official press photo"
    search_url = f"https://duckduckgo.com/?q={httpx.URL(query).params}&iax=images&ia=images"

    # Use a simple scrape of image CDNs for now
    # In production this would use a proper image search API
    image_candidates = [
        f"https://last.fm/music/{artist_name.replace(' ', '+')}/+images",
        f"https://www.allmusic.com/search/all/{artist_name.replace(' ', '+')}",
    ]
    return image_candidates


def research_concert(raw_input: str, ticket_url: str) -> ConcertInfo:
    """
    Main research function — uses Claude with tool use to gather concert info.
    """
    tools = [
        {
            "name": "web_search",
            "description": "Search the web for information about an artist or concert event",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        },
        {
            "name": "fetch_url",
            "description": "Fetch content from a URL",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"}
                },
                "required": ["url"]
            }
        }
    ]

    messages = [
        {
            "role": "user",
            "content": f"""Research this concert event and return structured JSON:

Event description: {raw_input}
Ticket purchase URL: {ticket_url}

{RESEARCH_PROMPT}"""
        }
    ]

    # Agentic loop
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
                    # Extract JSON from response
                    text = block.text
                    json_match = re.search(r'\{.*\}', text, re.DOTALL)
                    if json_match:
                        import json
                        data = json.loads(json_match.group())
                        data["ticket_url"] = ticket_url
                        return data
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "web_search":
                        result = _mock_search(block.input["query"])
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

    # Fallback: ask Claude to just parse what it knows
    fallback = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=2048,
        messages=[{
            "role": "user",
            "content": f"Based on this concert info, return structured JSON (no tools needed):\n{raw_input}\nTicket URL: {ticket_url}\n\n{RESEARCH_PROMPT}"
        }]
    )
    import json
    text = fallback.content[0].text
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        data = json.loads(json_match.group())
        data["ticket_url"] = ticket_url
        return data

    raise ValueError("Could not extract concert info from research agent")


def _mock_search(query: str) -> str:
    """Placeholder — replace with real search API (Serper, Brave, etc.)."""
    return f"Search results for '{query}': [Results would appear here with a real search API key configured in .env]"
