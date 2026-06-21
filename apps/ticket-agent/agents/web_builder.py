"""
Web Builder Agent — generates a world-class concert landing page.

Two-step approach:
  1. Prompt Architect (Claude Opus) builds a detailed, event-specific design brief
  2. Site Builder (Claude Opus) turns that brief into a complete single-file HTML page
"""
import re
import anthropic
from pathlib import Path

client = anthropic.Anthropic()

# ── Step 1: Prompt Architect ───────────────────────────────────────────────────

PROMPT_ARCHITECT_SYSTEM = """Ты — креативный директор ивент-агентства уровня HYPE, специализирующегося на концертных лендингах.
Ты создаёшь дизайн-бриф для верстальщика, который сделает сайт уровня Tomorrowland, Glastonbury, Coachella.

ОБЯЗАТЕЛЬНЫЕ БЛОКИ (все должны присутствовать):
1. НАВИГАЦИЯ — фиксированная, прозрачная, при скролле — тёмная с blur. Логотип + ссылки + кнопка "Купить" с градиентом. EN/RU переключатель языка.
2. HERO — полноэкранный, минимум 100vh. Фото артиста как фон с overlay. Анимированный заголовок (буквы появляются с задержкой). Aurora blobs (цветные размытые круги в bg). Частицы/эмберы. Дата + место. CTA кнопка.
3. MARQUEE — бегущая строка с ключевыми словами события (артист, место, дата, жанр).
4. ИСТОРИЯ / ОПИСАНИЕ — красивый блок с eyebrow label, большим заголовком и текстом о событии. Stats: годы на сцене, проданных альбомов, стран тура.
5. АТМОСФЕРА — параллакс фото-секция с цитатой о живом выступлении. Эмоциональный текст на русском.
6. ФОТО-ПОЛОСА — параллакс-фото концерта во всю ширину.
7. СКИДКА + CTA — Discount badge ({discount}%) + кнопка купить билеты. Prominently visible.
8. БИЛЕТЫ — две карточки с ценами (VIP и стандарт). Промокод. Список включений.
9. FAQ — раскрывающиеся вопросы-ответы о событии.
10. ЗАКРЫВАЮЩИЙ БЛОК — финальный призыв с большим текстом и кнопкой.
11. STICKY CTA — фиксированная кнопка "КУПИТЬ БИЛЕТЫ" внизу экрана на мобильных.
12. ФУТЕР — логотип, ссылки, дисклеймер.

ДИЗАЙН:
- Шрифты: Cinzel (заголовки, serif), Cormorant Garamond (italic accent), Inter (body)
- CSS переменные для всех цветов — палитра из 8-10 цветов, тёмная тема
- Цвета берёт из жанра и вайба артиста
- Анимации: fadeUp, частицы, aurora drift, draw для SVG, scroll reveals через IntersectionObserver
- Countdown timer в hero (дни/часы/минуты/секунды)
- Scroll reveal для всех секций
- Плавный скролл

КОНТЕНТ НА РУССКОМ, с возможностью переключить на английский через data-i18n атрибуты.

Выдай детальный дизайн-бриф на русском с конкретными:
- Цветовой палитрой (hex коды)
- Выбором шрифтов
- Описанием каждой секции
- Идеями для анимаций
- Текстами для атмосферного блока"""


PROMPT_ARCHITECT_USER = """Напиши дизайн-бриф для концертного лендинга:

Артист: {artist_name}
Событие: {event_title}
Дата: {date}
Место: {venue}, {city}, {country}
Жанр: {genre}
Описание: {description}
Скидка: {discount}%
URL билетов: {ticket_url}
Фото артиста (используй эти URL в img src): {image_urls}
Контекст из интернета: {web_context}

Создай вдохновляющий бриф для сайта уровня мирового фестиваля."""


# ── Step 2: Site Builder ───────────────────────────────────────────────────────

SITE_BUILDER_SYSTEM = """Ты — элитный frontend-разработчик. Ты создаёшь потрясающие одно-файловые HTML страницы уровня топовых мировых фестивалей.

ТЕХНИЧЕСКИЕ ТРЕБОВАНИЯ:
- Только HTML + CSS + vanilla JS (никаких фреймворков)
- Google Fonts через <link> в <head>: Cinzel, Cormorant Garamond, Inter
- Весь CSS в <style>, весь JS в <script> в конце body
- Mobile-first, полностью адаптивный
- Работает как локальный файл без сборки
- Выводи ТОЛЬКО чистый HTML, без markdown, без объяснений

ОБЯЗАТЕЛЬНАЯ СТРУКТУРА (все блоки must-have):

1. NAV — position:fixed, прозрачная, nav.scrolled добавляется при scroll>40px → тёмная с backdrop-filter:blur(14px). Кнопка-гамбургер на мобайл. Переключатель языка RU/EN.

2. HERO — min-height:100vh. .hero-photo{position:absolute;inset:0} с фото артиста. Aurora blobs (3 штуки, position:absolute, border-radius:50%, filter:blur(70px), animation:drift). Particle/ember эффект. Анимированный wordmark (буквы span с animation-delay). Countdown.

3. MARQUEE — overflow:hidden, animation:scroll linear infinite. Дублировать контент ×2 для бесшовного loop.

4. STORY SECTION — eyebrow label (маленький uppercase текст), большой h2 (Cinzel), параграф, stats grid (4 числа).

5. ATMOSPHERE — parallax фото через background-attachment:fixed, overlay градиент, цитата на русском в serif italic.

6. PHOTOBAND — высокая полоса с parallax фото.

7. TICKETS SECTION — 2 карточки: стандарт и VIP. Discount badge (круглый, градиент, анимация). Список включений через ul>li. Промокод.

8. FAQ — details/summary с анимацией .plus{transform:rotate(45deg)} при open. 5-6 вопросов.

9. CLOSING — текст-призыв + кнопка.

10. FOOTER — бренд, ссылки, дисклеймер.

11. STICKY CTA — position:fixed;bottom;z-index:900. Прячется при скролле к секции tickets.

JS ФУНКЦИОНАЛЬНОСТЬ:
- setLang(lang) функция для переключения RU/EN через data-i18n атрибуты и объект I18N с переводами
- Countdown timer setInterval каждую секунду
- IntersectionObserver для .reveal элементов → добавляет класс .in
- Nav scroll effect
- Ember/particle генерация через JS
- FAQ details toggle animation
- Wordmark буква-за-буквой анимация

CSS АНИМАЦИИ:
@keyframes fadeUp, @keyframes drift, @keyframes scroll (marquee), @keyframes rise (embers), @keyframes draw (SVG)

ВАЖНО: Sticky CTA кнопка ВСЕГДА видна. Discount {discount}% badge ВСЕГДА рядом с кнопкой покупки. Все ссылки на билеты → {ticket_url}. Язык страницы — РУССКИЙ по умолчанию."""


SITE_BUILDER_USER = """Создай концертный лендинг по этому дизайн-брифу:

{design_brief}

КРИТИЧНО:
- Скидка {discount}% — показать prominently в badge рядом с кнопкой
- Все ссылки на билеты: {ticket_url}
- Фото артиста: {image_urls}
- Язык по умолчанию: РУССКИЙ
- Переключатель RU/EN обязателен
- Countdown до даты события обязателен
- Aurora blobs + частицы в hero обязательны
- Sticky CTA кнопка обязательна
- Начни сразу с <!DOCTYPE html>, без объяснений"""


# ── Public API ─────────────────────────────────────────────────────────────────

def build_website(concert_info: dict) -> str:
    """
    Two-step pipeline: design brief → HTML page.
    Returns the complete HTML string.
    """
    discount = concert_info.get("discount", 15)
    image_urls = concert_info.get("image_urls", [])
    image_list = "\n".join(f"- {u}" for u in image_urls[:5]) if image_urls else "нет фото — использовать тёмный градиентный фон"

    edit_instructions = concert_info.get("_edit_instructions", "")

    # Step 1 — generate design brief
    brief_response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4000,
        system=PROMPT_ARCHITECT_SYSTEM,
        messages=[{
            "role": "user",
            "content": PROMPT_ARCHITECT_USER.format(
                artist_name=concert_info["artist_name"],
                event_title=concert_info["event_title"],
                date=concert_info["date"],
                venue=concert_info["venue"],
                city=concert_info["city"],
                country=concert_info["country"],
                genre=concert_info["genre"],
                description=concert_info["description"],
                discount=discount,
                ticket_url=concert_info["ticket_url"],
                image_urls=image_list,
                web_context=concert_info.get("web_context", "нет контекста")
            ) + (f"\n\nДОПОЛНИТЕЛЬНЫЕ ПРАВКИ ОТ ЗАКАЗЧИКА: {edit_instructions}" if edit_instructions else "")
        }]
    )
    design_brief = brief_response.content[0].text

    # Step 2 — build HTML from brief
    html_response = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=16000,
        system=SITE_BUILDER_SYSTEM.format(discount=discount, ticket_url=concert_info["ticket_url"]),
        messages=[{
            "role": "user",
            "content": SITE_BUILDER_USER.format(
                design_brief=design_brief,
                discount=discount,
                ticket_url=concert_info["ticket_url"],
                image_urls=image_list
            )
        }]
    )

    html = html_response.content[0].text
    html = re.sub(r'^```html\s*', '', html.strip())
    html = re.sub(r'\s*```$', '', html)

    return html


def save_website(html: str, artist_slug: str, output_dir: str = "/tmp/concert-sites") -> str:
    """Save HTML to disk and return the file path."""
    site_dir = Path(output_dir) / artist_slug
    site_dir.mkdir(parents=True, exist_ok=True)
    filepath = site_dir / "index.html"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return str(filepath)


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    return re.sub(r'-+', '-', slug).strip('-')
