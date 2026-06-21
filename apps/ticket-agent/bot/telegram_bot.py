"""
Telegram Bot — simplified workflow:

Flow 1: Deploy HTML
  1. Admin sends .html file
  2. Bot asks for ticket URL
  3. Bot inserts URL into all buy buttons in HTML
  4. Bot deploys to nginx → returns public URL

Flow 2: Post to social media
  1. Admin sends an image
  2. Bot asks for caption
  3. Bot asks for scheduled time (or "сейчас")
  4. Bot posts via Metricool / Telegram channel
"""
import os
import re
import logging
import tempfile
import shutil
from pathlib import Path
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

from agents.deployer import deploy_to_nginx

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


async def send_md(update: Update, text: str):
    await update.effective_message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


# ── State per chat ─────────────────────────────────────────────────────────────

# HTML deployment state
_pending_html: dict[int, dict] = {}   # chat_id → {"path": tmp_path, "slug": slug}

# Social posting state
_pending_image: dict[int, dict] = {}  # chat_id → {"path": tmp_path}
_pending_caption: dict[int, dict] = {} # chat_id → {"path": img_path, "caption": str}


def _slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    return re.sub(r'-+', '-', slug).strip('-') or "concert"


def _insert_ticket_url(html: str, ticket_url: str) -> str:
    """Replace all placeholder buy-button hrefs with the real ticket URL."""
    # Replace href="#" on buttons containing купить/buy/ticket keywords
    def replace_href(m):
        tag = m.group(0)
        if re.search(r'(купить|buy|ticket|билет)', tag, re.IGNORECASE):
            return re.sub(r'href=["\'][^"\']*["\']', f'href="{ticket_url}"', tag)
        return tag

    html = re.sub(r'<a[^>]+>', replace_href, html, flags=re.IGNORECASE)

    # Also replace any literal placeholder URLs
    html = re.sub(r'href=["\']#["\']', f'href="{ticket_url}"', html)
    html = html.replace("TICKET_URL_HERE", ticket_url)

    return html


# ── Command handlers ───────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_md(update,
        "🎫 *Бот публикации концертов*\n\n"
        "Что умею:\n\n"
        "📄 *Деплой сайта:*\n"
        "Отправь мне `.html` файл → я спрошу ссылку на билеты → опубликую на хостинг\n\n"
        "🖼 *Постинг в соцсети:*\n"
        "Отправь мне изображение → я спрошу подпись и время → опубликую через Metricool\n\n"
        "Команды: /status /cancel /help"
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, context)


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    _pending_html.pop(chat_id, None)
    _pending_image.pop(chat_id, None)
    _pending_caption.pop(chat_id, None)
    await send_md(update, "✅ Отменено. Жду новый файл.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    parts = []
    if chat_id in _pending_html:
        parts.append(f"⏳ Ожидаю ссылку на билеты для `{_pending_html[chat_id]['slug']}`")
    if chat_id in _pending_image:
        parts.append("⏳ Ожидаю подпись для изображения")
    if chat_id in _pending_caption:
        parts.append("⏳ Ожидаю время публикации")
    if not parts:
        parts.append("Нет активных задач. Пришли HTML или изображение.")
    await send_md(update, "\n".join(parts))


# ── Document handler (HTML files) ─────────────────────────────────────────────

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    doc = update.message.document
    fname = doc.file_name or "index.html"

    if not fname.lower().endswith(".html"):
        await send_md(update, "⚠️ Жду `.html` файл. Это не HTML.")
        return

    chat_id = update.effective_chat.id

    # Download file to tmp
    await send_md(update, "📥 Скачиваю файл...")
    file = await context.bot.get_file(doc.file_id)
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / fname
    await file.download_to_drive(str(tmp_path))

    # Derive slug from filename
    slug = _slugify(Path(fname).stem)

    _pending_html[chat_id] = {"path": str(tmp_path), "slug": slug, "tmp_dir": str(tmp_dir)}

    await send_md(update,
        f"✅ Файл получен: `{fname}`\n"
        f"🔗 Будет опубликован по адресу: `http://91.99.126.231/concerts/{slug}/`\n\n"
        "Теперь отправь *ссылку на покупку билетов* (начинается с `http`):\n"
        "_Она будет вставлена во все кнопки «Купить»_"
    )


# ── Photo handler ──────────────────────────────────────────────────────────────

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    chat_id = update.effective_chat.id

    # Get highest resolution photo
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    tmp_dir = Path(tempfile.mkdtemp())
    tmp_path = tmp_dir / "post_image.jpg"
    await file.download_to_drive(str(tmp_path))

    _pending_image[chat_id] = {"path": str(tmp_path), "tmp_dir": str(tmp_dir)}

    await send_md(update,
        "🖼 Изображение получено!\n\n"
        "Напиши *подпись к посту* (текст который опубликуется в соцсетях):"
    )


# ── Text handler ───────────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # ── Flow 1: waiting for ticket URL after HTML upload ──────────────────────
    if chat_id in _pending_html:
        if not text.startswith("http"):
            await send_md(update, "⚠️ Отправь ссылку, начинающуюся с `http`")
            return

        ticket_url = text
        state = _pending_html.pop(chat_id)
        slug = state["slug"]
        html_path = state["path"]
        tmp_dir = state["tmp_dir"]

        try:
            await send_md(update, "🔧 Вставляю ссылку в кнопки и публикую...")

            # Read, patch, write HTML
            with open(html_path, "r", encoding="utf-8") as f:
                html = f.read()

            html = _insert_ticket_url(html, ticket_url)

            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            # Deploy to nginx
            result = deploy_to_nginx(html_path, slug)
            site_url = result["subdomain_url"]

            await send_md(update,
                f"🚀 *Сайт опубликован!*\n\n"
                f"🌐 {site_url}\n\n"
                f"🎫 Ссылка на билеты вставлена во все кнопки"
            )
        except Exception as e:
            await send_md(update, f"❌ Ошибка при публикации: {e}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    # ── Flow 2a: waiting for caption after image upload ───────────────────────
    if chat_id in _pending_image:
        caption = text
        state = _pending_image.pop(chat_id)
        _pending_caption[chat_id] = {"path": state["path"], "tmp_dir": state["tmp_dir"], "caption": caption}

        await send_md(update,
            f"✅ Подпись сохранена:\n_{caption}_\n\n"
            "⏰ *Когда публиковать?*\n\n"
            "• `сейчас` — опубликовать немедленно\n"
            "• `20:00` — сегодня в 20:00\n"
            "• `2026-07-20 18:00` — конкретная дата и время"
        )
        return

    # ── Flow 2b: waiting for scheduled time ───────────────────────────────────
    if chat_id in _pending_caption:
        state = _pending_caption.pop(chat_id)
        caption = state["caption"]
        img_path = state["path"]
        tmp_dir = state["tmp_dir"]
        scheduled_time = None if text.lower() in ("сейчас", "now") else text

        try:
            await send_md(update, "📢 Публикую...")
            result = await _post_image(caption, img_path, scheduled_time, context.bot, chat_id)
            await send_md(update, result)
        except Exception as e:
            await send_md(update, f"❌ Ошибка при публикации: {e}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    await send_md(update,
        "Жду файл или изображение.\n"
        "Отправь `.html` для деплоя сайта или 🖼 картинку для постинга."
    )


async def _post_image(caption: str, img_path: str, scheduled_time, bot, chat_id: int) -> str:
    """Post image to configured social platforms."""
    import asyncio
    from agents.social_media import post_to_telegram_channel, post_via_metricool

    results = []

    # Metricool (if configured)
    if os.environ.get("METRICOOL_API_TOKEN"):
        captions_dict = {"telegram": caption, "instagram": caption, "twitter": caption}
        r = await asyncio.to_thread(
            post_via_metricool, captions_dict, img_path, {}, scheduled_time
        )
        results.append(r)
    elif os.environ.get("TELEGRAM_CHANNEL_ID"):
        r = await asyncio.to_thread(
            post_to_telegram_channel, caption, img_path
        )
        results.append(r)
    else:
        return "⚠️ Не настроены соцсети. Добавь `METRICOOL_API_TOKEN` или `TELEGRAM_CHANNEL_ID` в `.env`"

    posted = [r["platform"] for r in results if r.get("status") == "posted"]
    scheduled = [r["platform"] for r in results if r.get("status") == "scheduled"]
    skipped = [r["platform"] for r in results if r.get("status") in ("skipped", "error", "not_implemented_yet")]

    msg = "🎉 *Готово!*\n\n"
    if posted:
        msg += f"✅ Опубликовано: {', '.join(posted)}\n"
    if scheduled:
        t = scheduled_time or "сейчас"
        msg += f"⏰ Запланировано на {t}: {', '.join(scheduled)}\n"
    if skipped:
        msg += f"⚠️ Пропущено: {', '.join(skipped)}\n"
    return msg


# ── Main ───────────────────────────────────────────────────────────────────────

def run_bot():
    token = os.environ.get("TICKET_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started.")
    import asyncio
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(drop_pending_updates=True)
