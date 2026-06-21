"""
Orchestrator Agent — manages the full pipeline from raw input to published site + social posts.
Coordinates: Researcher → WebBuilder → (user approval) → Deployer → VideoRenderer → SocialMedia
"""
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Awaitable

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
    video_paths: dict = field(default_factory=dict)
    scheduled_time: str | None = None
    state: PipelineState = PipelineState.IDLE
    error: str | None = None


_sessions: dict[int, PipelineSession] = {}


def get_session(chat_id: int) -> PipelineSession | None:
    return _sessions.get(chat_id)


def create_session(chat_id: int, raw_input: str, ticket_url: str) -> PipelineSession:
    session = PipelineSession(chat_id=chat_id, raw_input=raw_input, ticket_url=ticket_url)
    _sessions[chat_id] = session
    return session


async def run_research(session: PipelineSession, send_update, send_file=None) -> bool:
    session.state = PipelineState.RESEARCHING
    await send_update("🔍 Собираю информацию об артисте и мероприятии...")

    try:
        session.concert_info = await asyncio.to_thread(
            research_concert, session.raw_input, session.ticket_url
        )
        info = session.concert_info
        summary = (
            f"✅ *Исследование завершено!*\n\n"
            f"🎤 *Артист:* {info['artist_name']}\n"
            f"🎫 *Событие:* {info['event_title']}\n"
            f"📅 *Дата:* {info['date']}\n"
            f"📍 *Место:* {info['venue']}, {info['city']}, {info['country']}\n"
            f"🎵 *Жанр:* {info['genre']}\n\n"
            f"_{info['description']}_"
        )
        await send_update(summary)
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Ошибка при сборе информации: {e}")
        return False


async def run_build_site(session: PipelineSession, send_update, send_file=None) -> bool:
    session.state = PipelineState.BUILDING_SITE
    await send_update("🎨 Создаю концертный лендинг... Это займёт около минуты.")

    try:
        html = await asyncio.to_thread(build_website, session.concert_info)
        session.html_content = html

        slug = slugify(session.concert_info["artist_name"])
        session.html_path = save_website(html, slug)

        session.state = PipelineState.AWAITING_APPROVAL

        # Send HTML file for preview
        if send_file:
            await send_file(
                session.html_path,
                caption=f"🎨 Лендинг для *{session.concert_info['event_title']}* — открой в браузере для предпросмотра"
            )

        await send_update(
            f"Что делаем дальше?\n"
            f"✅ *approve* — задеплоить и опубликовать\n"
            f"✏️ *правка: [что изменить]* — внести правки"
        )
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Ошибка при создании сайта: {e}")
        return False


async def run_deploy(session: PipelineSession, send_update, send_file=None) -> bool:
    session.state = PipelineState.DEPLOYING
    await send_update("🚀 Публикую сайт на хостинг...")

    try:
        slug = slugify(session.concert_info["artist_name"])
        session.deployment = await asyncio.to_thread(deploy, session.html_path, slug)

        url = session.deployment["subdomain_url"]
        await send_update(f"✅ *Сайт опубликован!*\n🌐 {url}")
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Ошибка при деплое: {e}")
        return False


async def run_render_video(session: PipelineSession, send_update, send_file=None) -> bool:
    await send_update("🎬 Рендерю промо-видео (15 сек)... Это займёт 1-2 минуты.")

    session.concert_info["site_url"] = session.deployment["subdomain_url"]

    try:
        paths = await asyncio.to_thread(render_all_formats, session.concert_info)
        session.video_paths = paths

        await send_update("🎬 *Видео готово!* Отправляю файлы...")

        if send_file:
            for fmt, path in paths.items():
                if not str(path).startswith("ERROR"):
                    label = {"square": "квадрат 1:1", "portrait": "портрет 9:16"}.get(fmt, fmt)
                    await send_file(path, caption=f"🎬 Промо-видео ({label})")

        return True
    except Exception as e:
        session.error = str(e)
        await send_update(f"❌ Ошибка при рендере видео: {e}")
        return False


async def run_social_publish(session: PipelineSession, send_update, send_file=None) -> bool:
    session.state = PipelineState.PUBLISHING_SOCIAL
    await send_update("📢 Публикую в социальные сети...")

    try:
        site_url = session.deployment["subdomain_url"]
        publish_result = await asyncio.to_thread(
            publish_all,
            session.concert_info,
            site_url,
            None,
            session.video_paths,
            session.scheduled_time,
        )
        session.social_results = publish_result["results"]

        posted = [r["platform"] for r in session.social_results if r.get("status") == "posted"]
        scheduled = [r["platform"] for r in session.social_results if r.get("status") == "scheduled"]
        skipped = [r["platform"] for r in session.social_results if r.get("status") in ("skipped", "error")]

        session.state = PipelineState.DONE
        msg = "🎉 *Готово! Всё опубликовано.*\n\n"
        if posted:
            msg += f"✅ Опубликовано: {', '.join(posted)}\n"
        if scheduled:
            msg += f"⏰ Запланировано: {', '.join(scheduled)}\n"
        if skipped:
            msg += f"⚠️ Пропущено: {', '.join(skipped)}\n"
        msg += f"\n🌐 Сайт: {site_url}\n🎫 Билеты: {session.concert_info['ticket_url']}"

        await send_update(msg)
        return True
    except Exception as e:
        session.state = PipelineState.FAILED
        session.error = str(e)
        await send_update(f"❌ Ошибка при публикации: {e}")
        return False
