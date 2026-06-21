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
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode

import sys
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


_waiting_for_url: dict[int, str] = {}


async def send_md(update: Update, text: str):
    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def make_notifiers(chat_id: int, bot):
    """Returns (send_update, send_file) callbacks for the given chat."""

    async def send_update(msg: str):
        await bot.send_message(chat_id, msg, parse_mode=ParseMode.MARKDOWN)

    async def send_file(path: str, caption: str = ""):
        try:
            with open(path, "rb") as f:
                await bot.send_document(
                    chat_id,
                    document=f,
                    filename=os.path.basename(path),
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            await bot.send_message(chat_id, f"⚠️ Не удалось отправить файл: {e}")

    return send_update, send_file


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_md(update,
        "🎫 *Агент продажи билетов*\n\n"
        "Отправь мне описание концерта и я создам лендинг + опубликую везде.\n\n"
        "Используй `/event <описание>` для старта.\n\n"
        "_Пример:_ `/event Coldplay, Лужники Москва, 20 июля 2025`"
    )


async def cmd_event(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Нет доступа.")
        return

    if not context.args:
        await send_md(update, "Использование: `/event <описание концерта>`")
        return

    description = " ".join(context.args)
    chat_id = update.effective_chat.id
    _waiting_for_url[chat_id] = description

    await send_md(update,
        f"Принято! 🎤\n\n*Событие:* {description}\n\n"
        "Теперь отправь *ссылку на покупку билетов:*"
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session(update.effective_chat.id)
    if not session:
        await send_md(update, "Нет активного процесса. Используй `/event` для старта.")
        return
    await send_md(update, f"*Статус:* `{session.state.value}`")


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    _waiting_for_url.pop(chat_id, None)
    await send_md(update, "Процесс отменён. Используй `/event` для нового события.")


# ── Message handler ────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # ── Waiting for ticket URL ────────────────────────────────────────────────
    if chat_id in _waiting_for_url:
        if not text.startswith("http"):
            await send_md(update, "⚠️ Отправь корректную ссылку, начинающуюся с `http`")
            return

        raw_input = _waiting_for_url.pop(chat_id)
        ticket_url = text
        session = create_session(chat_id, raw_input, ticket_url)

        notify, send_file = make_notifiers(chat_id, context.bot)

        ok = await run_research(session, notify, send_file)
        if ok:
            await run_build_site(session, notify, send_file)
        return

    # ── Approval / edit flow ──────────────────────────────────────────────────
    session = get_session(chat_id)
    if session and session.state == PipelineState.AWAITING_APPROVAL:
        lower = text.lower()

        if lower in ("approve", "да", "yes", "ok", "✅", "deploy", "опубликовать"):
            notify, send_file = make_notifiers(chat_id, context.bot)

            ok = await run_deploy(session, notify, send_file)
            if ok:
                ok = await run_render_video(session, notify, send_file)
            if ok:
                await send_md(update,
                    "⏰ *На какое время запланировать публикацию?*\n\n"
                    "Напиши время в формате: `пост 20:00` или `пост 2025-07-20 18:00`\n"
                    "Или напиши `пост сейчас` для немедленной публикации."
                )

        elif lower.startswith("пост ") or lower.startswith("post "):
            time_str = re.sub(r'^(пост|post)\s+', '', lower).strip()
            notify, send_file = make_notifiers(chat_id, context.bot)

            if time_str in ("сейчас", "now"):
                session.scheduled_time = None
            else:
                session.scheduled_time = time_str

            await run_social_publish(session, notify, send_file)

        elif lower.startswith("edit:") or lower.startswith("правка:"):
            instructions = re.sub(r'^(edit:|правка:)\s*', '', text, flags=re.IGNORECASE).strip()
            await send_md(update, f"✏️ Применяю правки: _{instructions}_\n\nПересоздаю сайт...")

            session.concert_info["_edit_instructions"] = instructions
            notify, send_file = make_notifiers(chat_id, context.bot)
            await run_build_site(session, notify, send_file)

        else:
            await send_md(update,
                "Ответь:\n"
                "✅ *approve* — задеплоить сайт\n"
                "✏️ *правка: [что изменить]* — внести правки"
            )
        return

    await send_md(update, "Используй `/event <описание>` чтобы начать новый концертный проект.")


# ── Main ───────────────────────────────────────────────────────────────────────

def run_bot():
    token = os.environ.get("TICKET_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("event", cmd_event))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started.")
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(drop_pending_updates=True)
