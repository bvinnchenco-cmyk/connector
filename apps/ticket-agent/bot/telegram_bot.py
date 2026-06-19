"""
Telegram Bot — entry point for the concert ticket agent pipeline.

Usage flow:
  1. Admin sends: /event <description>
  2. Bot asks for ticket URL
  3. Pipeline runs: Research → Build Site → Approval → Deploy → Social
"""
import os
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import (
    create_session,
    get_session,
    run_research,
    run_build_site,
    run_deploy,
    run_render_video,
    run_social_publish,
    PipelineState,
)
import re

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_admin_ids() -> set[int]:
    raw = os.environ.get("ADMIN_TELEGRAM_IDS", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip().isdigit()}


def is_admin(user_id: int) -> bool:
    admin_ids = get_admin_ids()
    return not admin_ids or user_id in admin_ids


# ── State machine: waiting for ticket URL ──────────────────────────────────────
_waiting_for_url: dict[int, str] = {}  # chat_id → raw_event_description


async def send_md(update: Update, text: str):
    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_md(update,
        "🎫 *Concert Ticket Agent*\n\n"
        "Send me a concert event and I'll build a landing page + publish it everywhere.\n\n"
        "Use `/event <description>` to start.\n\n"
        "_Example:_ `/event Coldplay World Tour 2025 at Madison Square Garden on July 20`"
    )


async def cmd_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Not authorized.")
        return

    if not context.args:
        await send_md(update, "Usage: `/event <concert description>`")
        return

    description = " ".join(context.args)
    chat_id = update.effective_chat.id
    _waiting_for_url[chat_id] = description

    await send_md(update,
        f"Got it! 🎤\n\n*Event:* {description}\n\n"
        "Now send me the *ticket purchase URL* (e.g. ticketmaster link):"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_chat.id)
    if not session:
        await send_md(update, "No active pipeline. Use `/event` to start.")
        return
    await send_md(update, f"*Status:* `{session.state.value}`")


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    _waiting_for_url.pop(chat_id, None)
    await send_md(update, "Pipeline cancelled. Use `/event` to start a new one.")


# ── Message handler ────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # ── Waiting for ticket URL ────────────────────────────────────────────────
    if chat_id in _waiting_for_url:
        if not text.startswith("http"):
            await send_md(update, "⚠️ Please send a valid URL starting with `http`")
            return

        raw_input = _waiting_for_url.pop(chat_id)
        ticket_url = text
        session = create_session(chat_id, raw_input, ticket_url)

        async def notify(msg: str):
            await context.bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

        # Start pipeline
        ok = await run_research(session, notify)
        if ok:
            await run_build_site(session, notify)
        return

    # ── Approval / edit flow ──────────────────────────────────────────────────
    session = get_session(chat_id)
    if session and session.state == PipelineState.AWAITING_APPROVAL:
        lower = text.lower()

        if lower in ("approve", "да", "yes", "ok", "✅", "deploy", "опубликовать"):
            async def notify(msg: str):
                await context.bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

            ok = await run_deploy(session, notify)
            if ok:
                ok = await run_render_video(session, notify)
            if ok:
                # Ask for publishing time before posting
                await send_md(update,
                    "⏰ *На какое время запланировать публикацию?*\n\n"
                    "Напиши время в формате: `пост 20:00` или `пост 2025-07-20 18:00`\n"
                    "Или напиши `пост сейчас` для немедленной публикации."
                )

        elif lower.startswith("пост ") or lower.startswith("post "):
            # Parse scheduled time from user message
            time_str = re.sub(r'^(пост|post)\s+', '', lower).strip()
            session = get_session(chat_id)

            async def notify(msg: str):
                await context.bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

            if time_str in ("сейчас", "now"):
                session.scheduled_time = None
            else:
                session.scheduled_time = time_str  # Metricool/social agents handle parsing

            await run_social_publish(session, notify)

        elif lower.startswith("edit:"):
            instructions = text[5:].strip()
            await send_md(update, f"✏️ Applying edits: _{instructions}_\n\nRebuilding...")

            from ..agents.web_builder import build_website, save_website, slugify
            import asyncio

            prompt_addition = f"\n\nUser requested these changes: {instructions}"
            session.concert_info["_edit_instructions"] = prompt_addition

            async def notify(msg: str):
                await context.bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

            await run_build_site(session, notify)

        else:
            await send_md(update,
                "Reply with:\n"
                "✅ *approve* — deploy the site\n"
                "✏️ *edit: [what to change]* — request changes"
            )
        return

    await send_md(update, "Use `/event <description>` to start a new concert pipeline.")


# ── Main ───────────────────────────────────────────────────────────────────────

def run_bot():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("event", cmd_event))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started.")
    app.run_polling(drop_pending_updates=True)
