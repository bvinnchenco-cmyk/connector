"""
Orchestrator Agent — manages the full pipeline from raw input to published site + social posts.
Coordinates: Researcher → WebBuilder → (user approval) → Deployer → SocialMedia
"""
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

from agents.researcher import research_concert
from agents.web_builder import build_website, save_website, slugify
from agents.deployer import deploy
from agents.social_media import publish_all
from agents.video_renderer import render_all_formats

logger = logging.getLogger(__name__)


class PipelineState(Enum):
    IDLE = "idle"
    RESEARCHING = "researching"
    BUILDING_SITE = "building_site"
    AWAITING_APPROVAL = "awaiting_approval"
    DEPLOYING = "deploying"
    PUBLISHING_SOCIAL = "publishing_social"
    DONE = "done"
    FAILED = "failed"


@dataclass
class PipelineSession:
    chat_id: int
    raw_input: str
    ticket_url: str
    concert_info: dict | None = None
    html_content: str | None = None
    html_path: str | None = None
    deployment: dict | None = None
    social_results: list = field(default_factory=list)
    video_paths: dict = field(default_factory=dict)   # {"square": "/tmp/...", "portrait": "/tmp/..."}
    scheduled_time: str | None = None                 # ISO 8601, set by user before publishing
    state: PipelineState = PipelineState.IDLE
    error: str | None = None


# In-memory session store (one active session per Telegram chat_id)
_sessions: dict[int, PipelineSession] = {}


def get_session(chat_id: int) -> PipelineSession | None:
    return _sessions.get(chat_id)


def create_session(chat_id: int, raw_input: str, ticket_url: str) -> PipelineSession:
    session = PipelineSession(chat_id=chat_id, raw_input=raw_input, ticket_url=ticket_url)
    _sessions[chat_id] = session
    return session


async def run_research(session: PipelineSession, send_update) -> bool:
    """Step 1: Research the concert."""
    session.state = PipelineState.RESEARCHING
    await send_update("🔍 Researching artist and event details...")

    try:
        session.concert_info = await asyncio.to_thread(
            research_concert, session.raw_input, session.ticket_url
        )
        info = session.concert_info
        summary = (
            f"✅ *Research complete!*\n\n"
            f"🎤 *Artist:* {info['artist_name']}\n"
            f"🎫 *Event:* {info['event_title']}\n"
            f"📅 *Date:* {info['date']}\n"
            f"📍 *Venue:* {info['venue']}, {info['city']}, {info['country']}\n"
            f"🎵 *Genre:* {info['genre']}\n\n"
            f"_{info['description']}_"
        )
        await send_update(summary)
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Research failed: {e}")
        return False


async def run_build_site(session: PipelineSession, send_update) -> bool:
    """Step 2: Build the website."""
    session.state = PipelineState.BUILDING_SITE
    await send_update("🎨 Building your concert landing page...")

    try:
        html = await asyncio.to_thread(build_website, session.concert_info)
        session.html_content = html

        slug = slugify(session.concert_info["artist_name"])
        session.html_path = save_website(html, slug)

        session.state = PipelineState.AWAITING_APPROVAL
        await send_update(
            f"✅ *Website ready!*\n\n"
            f"The page has been generated for *{session.concert_info['event_title']}*.\n\n"
            f"Reply with:\n"
            f"✅ *approve* — to deploy and publish\n"
            f"✏️ *edit: [instructions]* — to request changes"
        )
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Site build failed: {e}")
        return False


async def run_deploy(session: PipelineSession, send_update) -> bool:
    """Step 3: Deploy to hosting."""
    session.state = PipelineState.DEPLOYING
    await send_update("🚀 Deploying site to hosting...")

    try:
        slug = slugify(session.concert_info["artist_name"])
        session.deployment = await asyncio.to_thread(deploy, session.html_path, slug)

        url = session.deployment["subdomain_url"]
        await send_update(f"✅ *Site deployed!*\n🌐 {url}")
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Deployment failed: {e}")
        return False


async def run_render_video(session: PipelineSession, send_update) -> bool:
    """Step 3b: Render cinematic promo video via Remotion."""
    await send_update("🎬 Рендерю промо-видео (15 сек)... Это займёт 1-2 минуты.")

    # Pass site_url into concert_info so video shows it
    session.concert_info["site_url"] = session.deployment["subdomain_url"]

    try:
        paths = await asyncio.to_thread(render_all_formats, session.concert_info)
        session.video_paths = paths

        lines = []
        for fmt, path in paths.items():
            status = "✅" if not path.startswith("ERROR") else "❌"
            lines.append(f"{status} {fmt}: `{path}`")

        await send_update(
            "🎬 *Видео готово!*\n\n"
            + "\n".join(lines)
            + "\n\nПосмотри результат и напиши *approve* для публикации или *edit video: [что изменить]*"
        )
        return True
    except Exception as e:
        session.error = str(e)
        await send_update(f"❌ Рендер видео упал: {e}")
        return False


async def run_social_publish(session: PipelineSession, send_update) -> bool:
    """Step 4: Publish social media posts."""
    session.state = PipelineState.PUBLISHING_SOCIAL
    await send_update("📢 Publishing to social media...")

    try:
        site_url = session.deployment["subdomain_url"]
        publish_result = await asyncio.to_thread(
            publish_all,
            session.concert_info,
            site_url,
            None,                      # image_path — TODO: add poster generation
            session.video_paths,
            session.scheduled_time,
        )
        session.social_results = publish_result["results"]
        captions = publish_result["captions"]

        posted = [r["platform"] for r in session.social_results if r.get("status") == "posted"]
        skipped = [r["platform"] for r in session.social_results if r.get("status") in ("skipped", "error")]

        session.state = PipelineState.DONE
        msg = "🎉 *Готово!*\n\n"
        if posted:
            msg += f"✅ Опубликовано: {', '.join(posted)}\n"
        if skipped:
            msg += f"⚠️ Пропущено: {', '.join(skipped)}\n"
        msg += f"\n🌐 Сайт: {site_url}\n🎫 Билеты: {session.concert_info['ticket_url']}"

        await send_update(msg)
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Social publishing failed: {e}")
        return False
