"""
Voice synthesis with voice cloning using Coqui XTTS v2.
XTTS can speak 13+ languages while cloning the original speaker's voice
from just a short audio sample (6+ seconds).
Free, local, no API needed.
"""
import asyncio
import os
from functools import lru_cache
from pathlib import Path

# Language code mapping: ISO 639-1 → XTTS language id
XTTS_LANG_MAP = {
    "en": "en", "ru": "ru", "fr": "fr", "de": "de", "es": "es",
    "it": "it", "pt": "pt", "pl": "pl", "tr": "tr", "nl": "nl",
    "cs": "cs", "ar": "ar", "zh": "zh-cn", "ja": "ja", "ko": "ko",
    "th": "th", "vi": "vi", "hu": "hu",
}

DEFAULT_VOICE = str(Path(__file__).parent / "default_voice.wav")


@lru_cache(maxsize=1)
def get_tts():
    from TTS.api import TTS
    return TTS("tts_models/multilingual/multi-dataset/xtts_v2", gpu=False)


async def synthesize_voice(
    text: str,
    target_lang: str,
    voice_sample_path: str | None,
    output_path: str,
) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _synthesize_sync, text, target_lang, voice_sample_path, output_path
    )


def _synthesize_sync(
    text: str,
    target_lang: str,
    voice_sample_path: str | None,
    output_path: str,
) -> str:
    tts = get_tts()

    lang = XTTS_LANG_MAP.get(target_lang.split("-")[0], "en")

    # Use user's voice sample if available, else default voice
    speaker_wav = voice_sample_path if (voice_sample_path and os.path.exists(voice_sample_path)) \
        else DEFAULT_VOICE

    tts.tts_to_file(
        text=text,
        speaker_wav=speaker_wav,
        language=lang,
        file_path=output_path,
    )
    return output_path
