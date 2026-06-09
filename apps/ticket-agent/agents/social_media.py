"""
Social Media Agent — creates and publishes event posts to Twitter/X, Instagram, Threads.
"""
import os
import httpx
import anthropic
from pathlib import Path

client = anthropic.Anthropic()


CAPTION_PROMPT = """Write a compelling social media post for this concert event.

Artist: {artist_name}
Event: {event_title}
Date: {date}
Venue: {venue}, {city}
Site URL: {site_url}
Ticket URL: {ticket_url}

Write 3 versions:
1. Twitter/X (max 280 chars, include hashtags, ticket link)
2. Instagram caption (longer, emotive, hashtags at end)
3. Threads (conversational, 500 chars max)

Return as JSON:
{{"twitter": "...", "instagram": "...", "threads": "..."}}"""


def generate_captions(concert_info: dict, site_url: str) -> dict:
    """Use Claude to generate platform-specific captions."""
    prompt = CAPTION_PROMPT.format(
        artist_name=concert_info["artist_name"],
        event_title=concert_info["event_title"],
        date=concert_info["date"],
        venue=concert_info["venue"],
        city=concert_info["city"],
        site_url=site_url,
        ticket_url=concert_info["ticket_url"]
    )

    response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    import json, re
    text = response.content[0].text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {"twitter": text[:280], "instagram": text, "threads": text[:500]}


def post_to_twitter(caption: str, image_path: str | None = None) -> dict:
    """Post to Twitter/X using API v2."""
    api_key = os.environ["TWITTER_API_KEY"]
    api_secret = os.environ["TWITTER_API_SECRET"]
    access_token = os.environ["TWITTER_ACCESS_TOKEN"]
    access_secret = os.environ["TWITTER_ACCESS_SECRET"]

    import tweepy
    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)
    client_v2 = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret
    )

    media_ids = []
    if image_path and Path(image_path).exists():
        media = api.media_upload(image_path)
        media_ids.append(media.media_id)

    tweet = client_v2.create_tweet(
        text=caption,
        media_ids=media_ids if media_ids else None
    )
    return {"platform": "twitter", "id": tweet.data["id"], "status": "posted"}


def post_to_instagram(caption: str, image_path: str) -> dict:
    """Post to Instagram using instagrapi."""
    from instagrapi import Client as InstaClient
    ig = InstaClient()
    ig.login(os.environ["INSTAGRAM_USERNAME"], os.environ["INSTAGRAM_PASSWORD"])

    media = ig.photo_upload(image_path, caption)
    return {"platform": "instagram", "id": str(media.pk), "status": "posted"}


def post_to_threads(caption: str, image_path: str | None = None) -> dict:
    """Post to Threads using Meta Threads API."""
    access_token = os.environ.get("THREADS_ACCESS_TOKEN")
    user_id = os.environ.get("THREADS_USER_ID")

    if not access_token or not user_id:
        return {"platform": "threads", "status": "skipped", "reason": "credentials not set"}

    with httpx.Client() as http:
        # Step 1: create container
        container_resp = http.post(
            f"https://graph.threads.net/v1.0/{user_id}/threads",
            params={
                "media_type": "TEXT",
                "text": caption,
                "access_token": access_token
            }
        )
        container_resp.raise_for_status()
        container_id = container_resp.json()["id"]

        # Step 2: publish
        pub_resp = http.post(
            f"https://graph.threads.net/v1.0/{user_id}/threads_publish",
            params={
                "creation_id": container_id,
                "access_token": access_token
            }
        )
        pub_resp.raise_for_status()

    return {"platform": "threads", "id": pub_resp.json()["id"], "status": "posted"}


def publish_all(concert_info: dict, site_url: str, promo_image_path: str | None = None) -> list[dict]:
    """Generate captions and post to all configured platforms."""
    captions = generate_captions(concert_info, site_url)
    results = []

    if os.environ.get("TWITTER_API_KEY"):
        try:
            results.append(post_to_twitter(captions["twitter"], promo_image_path))
        except Exception as e:
            results.append({"platform": "twitter", "status": "error", "error": str(e)})

    if os.environ.get("INSTAGRAM_USERNAME") and promo_image_path:
        try:
            results.append(post_to_instagram(captions["instagram"], promo_image_path))
        except Exception as e:
            results.append({"platform": "instagram", "status": "error", "error": str(e)})

    if os.environ.get("THREADS_ACCESS_TOKEN"):
        try:
            results.append(post_to_threads(captions["threads"], promo_image_path))
        except Exception as e:
            results.append({"platform": "threads", "status": "error", "error": str(e)})

    return results
