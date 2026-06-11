"""
Translation — completely free, no API keys needed.

Priority chain:
  1. LibreTranslate (self-hosted via Docker — unlimited, offline)
  2. deep-translator GoogleTranslator (unofficial scraping — no key)
  3. deep-translator MyMemoryTranslator (free public API — 5k chars/day)
"""
import os
import asyncio
import httpx
from deep_translator import GoogleTranslator, MyMemoryTranslator, LibreTranslator

LIBRETRANSLATE_URL = os.getenv("LIBRETRANSLATE_URL", "http://libretranslate:5000")

# LibreTranslate supported languages (subset — most common)
LIBRE_SUPPORTED = {
    "en", "ru", "fr", "de", "es", "it", "pt", "pl", "nl",
    "ar", "zh", "ja", "ko", "tr", "vi", "th", "hi", "uk",
}


async def translate_text(text: str, target_lang: str, source_lang: str | None = None) -> str:
    if not text.strip():
        return text

    src = (source_lang or "auto").split("-")[0].lower()
    tgt = target_lang.split("-")[0].lower()

    if src == tgt:
        return text

    return await asyncio.get_event_loop().run_in_executor(
        None, _translate_sync, text, tgt, src
    )


def _translate_sync(text: str, target: str, source: str) -> str:
    # 1. LibreTranslate (self-hosted, unlimited)
    if target in LIBRE_SUPPORTED:
        try:
            translator = LibreTranslator(
                source=source if source in LIBRE_SUPPORTED else "auto",
                target=target,
                base_url=LIBRETRANSLATE_URL,
            )
            result = translator.translate(text)
            if result:
                return result
        except Exception as e:
            print(f"LibreTranslate failed: {e}, trying fallback")

    # 2. Google Translate unofficial (free, no key, ~500k chars/day soft limit)
    try:
        result = GoogleTranslator(source="auto", target=target).translate(text)
        if result:
            return result
    except Exception as e:
        print(f"GoogleTranslator failed: {e}, trying MyMemory")

    # 3. MyMemory (free public, 5k chars/day)
    try:
        lang_pair = f"{source}|{target}"
        result = MyMemoryTranslator(source=lang_pair.split("|")[0], target=lang_pair.split("|")[1]).translate(text)
        if result:
            return result
    except Exception as e:
        print(f"MyMemory failed: {e}")

    return text  # return original if all fail
