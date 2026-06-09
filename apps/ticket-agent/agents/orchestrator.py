"""
Orchestrator Agent — manages the full pipeline from raw input to published site + social posts.
Coordinates: Researcher → WebBuilder → (user approval) → Deployer → SocialMedia
"""
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum

from .researcher import research_concert, ConcertInfo
from .web_builder import build_website, save_website, slugify
from .deployer import deploy
from .social_media import publish_all

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
    concert_info: ConcertInfo | None = None
    html_content: str | None = None
    html_path: str | None = None
    deployment: dict | None = None
    social_results: list = field(default_factory=list)
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


async def run_social_publish(session: PipelineSession, send_update) -> bool:
    """Step 4: Publish social media posts."""
    session.state = PipelineState.PUBLISHING_SOCIAL
    await send_update("📢 Publishing to social media...")

    try:
        site_url = session.deployment["subdomain_url"]
        results = await asyncio.to_thread(
            publish_all, session.concert_info, site_url, None
        )
        session.social_results = results

        posted = [r["platform"] for r in results if r.get("status") == "posted"]
        skipped = [r["platform"] for r in results if r.get("status") in ("skipped", "error")]

        session.state = PipelineState.DONE
        msg = f"🎉 *All done!*\n\n"
        if posted:
            msg += f"✅ Posted to: {', '.join(posted)}\n"
        if skipped:
            msg += f"⚠️ Skipped: {', '.join(skipped)}\n"
        msg += f"\n🌐 Site: {site_url}\n🎫 Tickets: {session.concert_info['ticket_url']}"

        await send_update(msg)
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Social publishing failed: {e}")
        return False
