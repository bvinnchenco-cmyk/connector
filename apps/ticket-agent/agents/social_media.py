"""
Social Media Agent — free-tier publishers for testing before Metricool.

Phase 1 (current):
  - Telegram channel (Bot API, free, unlimited)
  - Twitter/X (Tweepy, free tier: 1500 posts/month)

Phase 2 (future):
  - Metricool API (replaces all of the above with one call)
"""
import os
import json
import re
import httpx
import asyncio
import anthropic
from pathlib import Path

client = anthropic.Anthropic()


# ── Caption generator ──────────────────────────────────────────────────────────

CAPTION_PROMPT = """Напиши тексты для постов в соцсетях для этого концертного события.

Артист: {artist_name}
Событие: {event_title}
Дата: {date}
Место: {venue}, {city}
Сайт: {site_url}
Ссылка на билеты: {ticket_url}
Скидка: {discount}%

Напиши 3 варианта на русском языке:
1. Telegram (до 1024 символов, можно эмодзи, ссылка на сайт в конце)
2. Twitter/X (до 270 символов, хэштеги, ссылка на билеты)
3. Instagram (длинный эмоциональный текст, хэштеги в конце)

Верни ТОЛЬКО JSON:
{{"telegram": "...", "twitter": "...", "instagram": "..."}}"""


def generate_captions(concert_info: dict, site_url: str) -> dict:
    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": CAPTION_PROMPT.format(
                artist_name=concert_info["artist_name"],
                event_title=concert_info["event_title"],
                date=concert_info["date"],
                venue=concert_info["venue"],
                city=concert_info["city"],
                site_url=site_url,
                ticket_url=concert_info["ticket_url"],
                discount=concert_info.get("discount", 15),
            )
        }]
    )
    text = response.content[0].text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    # Fallback
    short = f"🎫 {concert_info['artist_name']} — {concert_info['date']}, {concert_info['city']}\n{site_url}"
    return {"telegram": short, "twitter": short[:270], "instagram": short}


# ── Telegram channel publisher ─────────────────────────────────────────────────

async def _tg_send_photo(bot_token: str, channel_id: str, caption: str, image_path: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    async with httpx.AsyncClient(timeout=30) as http:
        with open(image_path, "rb") as f:
            resp = await http.post(url, data={"chat_id": channel_id, "caption": caption, "parse_mode": "Markdown"}, files={"photo": f})
        resp.raise_for_status()
        return resp.json()


async def _tg_send_video(bot_token: str, channel_id: str, caption: str, video_path: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    async with httpx.AsyncClient(timeout=120) as http:
        with open(video_path, "rb") as f:
            resp = await http.post(url, data={"chat_id": channel_id, "caption": caption, "parse_mode": "Markdown"}, files={"video": f})
        resp.raise_for_status()
        return resp.json()


async def _tg_send_text(bot_token: str, channel_id: str, text: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as http:
        resp = await http.post(url, json={"chat_id": channel_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": False})
        resp.raise_for_status()
        return resp.json()


def post_to_telegram_channel(
    caption: str,
    image_path: str | None = None,
    video_path: str | None = None,
) -> dict:
    """
    Posts to a Telegram channel using the existing bot token.
    Requires TELEGRAM_CHANNEL_ID in .env (e.g. @mychannel or -100123456789)
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TICKET_BOT_TOKEN")
    channel_id = os.environ["TELEGRAM_CHANNEL_ID"]

    if not token:
        return {"platform": "telegram_channel", "status": "skipped", "reason": "no bot token"}

    results = []

    # Post image first (if available)
    if image_path and Path(image_path).exists():
        r = asyncio.run(_tg_send_photo(token, channel_id, caption, image_path))
        results.append(r)

    # Post video separately
    if video_path and Path(video_path).exists():
        r = asyncio.run(_tg_send_video(token, channel_id, "🎬 Атмосфера события:", video_path))
        results.append(r)

    # If no media, post text only
    if not results:
        r = asyncio.run(_tg_send_text(token, channel_id, caption))
        results.append(r)

    return {"platform": "telegram_channel", "status": "posted", "message_ids": [r.get("result", {}).get("message_id") for r in results]}


# ── Twitter/X publisher ────────────────────────────────────────────────────────

def post_to_twitter(caption: str, image_path: str | None = None) -> dict:
    """
    Posts to Twitter/X using Tweepy.
    Free tier: 1500 posts/month. Requires 4 keys in .env.
    """
    try:
        import tweepy
    except ImportError:
        return {"platform": "twitter", "status": "skipped", "reason": "tweepy not installed"}

    api_key = os.environ.get("TWITTER_API_KEY")
    api_secret = os.environ.get("TWITTER_API_SECRET")
    access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
    access_secret = os.environ.get("TWITTER_ACCESS_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        return {"platform": "twitter", "status": "skipped", "reason": "credentials not set in .env"}

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    client_v2 = tweepy.Client(
        consumer_key=api_key, consumer_secret=api_secret,
        access_token=access_token, access_token_secret=access_secret
    )

    media_ids = []
    if image_path and Path(image_path).exists():
        media = api_v1.media_upload(image_path)
        media_ids.append(media.media_id)

    tweet = client_v2.create_tweet(
        text=caption[:270],
        media_ids=media_ids or None
    )
    return {"platform": "twitter", "status": "posted", "tweet_id": tweet.data["id"]}


# ── Metricool (Phase 2 — placeholder) ─────────────────────────────────────────

def post_via_metricool(
    captions: dict,
    image_path: str | None,
    video_paths: dict,
    scheduled_time: str | None = None,
) -> dict:
    """
    Phase 2: send everything to Metricool API in one call.
    scheduled_time: ISO 8601 string e.g. "2025-07-20T18:00:00+03:00"
    """
    api_token = os.environ.get("METRICOOL_API_TOKEN")
    blog_id = os.environ.get("METRICOOL_BLOG_ID")

    if not api_token or not blog_id:
        return {"platform": "metricool", "status": "skipped", "reason": "METRICOOL_API_TOKEN / METRICOOL_BLOG_ID not set"}

    # TODO: implement when Metricool API access is confirmed
    # POST https://app.metricool.com/api/v2/scheduler/posts
    return {"platform": "metricool", "status": "not_implemented_yet"}


# ── Main publish function ──────────────────────────────────────────────────────

def publish_all(
    concert_info: dict,
    site_url: str,
    image_path: str | None = None,
    video_paths: dict | None = None,
    scheduled_time: str | None = None,
) -> dict:
    """
    Generates captions and publishes to all configured platforms.
    Returns {"captions": {...}, "results": [...]}
    """
    captions = generate_captions(concert_info, site_url)
    video_path_square = (video_paths or {}).get("square")
    results = []

    # Phase 2: if Metricool is configured, use it exclusively
    if os.environ.get("METRICOOL_API_TOKEN"):
        r = post_via_metricool(captions, image_path, video_paths or {}, scheduled_time)
        results.append(r)
        return {"captions": captions, "results": results}

    # Phase 1: free tools
    if os.environ.get("TELEGRAM_CHANNEL_ID"):
        try:
            r = post_to_telegram_channel(captions["telegram"], image_path, video_path_square)
            results.append(r)
        except Exception as e:
            results.append({"platform": "telegram_channel", "status": "error", "error": str(e)})

    if os.environ.get("TWITTER_API_KEY"):
        try:
            r = post_to_twitter(captions["twitter"], image_path)
            results.append(r)
        except Exception as e:
            results.append({"platform": "twitter", "status": "error", "error": str(e)})

    return {"captions": captions, "results": results}
