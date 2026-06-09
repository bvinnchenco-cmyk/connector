"""
Translation using Google Translate API (free: 500k chars/month)
"""
import os
import httpx

GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")


async def translate_text(text: str, target_lang: str, source_lang: str | None = None) -> str:
    if not text.strip():
        return text

    params: dict = {
        "q": text,
        "target": target_lang,
        "format": "text",
        "key": GOOGLE_TRANSLATE_API_KEY,
    }
    if source_lang:
        params["source"] = source_lang.split("-")[0]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://translation.googleapis.com/language/translate/v2",
            json=params,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"]["translations"][0]["translatedText"]
