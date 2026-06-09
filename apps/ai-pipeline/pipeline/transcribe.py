"""
Transcription using faster-whisper (free, local, no API limits)
Falls back to Google Speech-to-Text if needed.
"""
import asyncio
from functools import lru_cache
from faster_whisper import WhisperModel


@lru_cache(maxsize=1)
def get_model() -> WhisperModel:
    # "base" model: ~74MB, good quality, fast on CPU
    # upgrade to "small" or "medium" for better accuracy
    return WhisperModel("base", device="cpu", compute_type="int8")


async def transcribe_audio(file_path: str, language_code: str | None = None) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _transcribe_sync, file_path, language_code)


def _transcribe_sync(file_path: str, language_code: str | None) -> str:
    model = get_model()
    lang = language_code.split("-")[0] if language_code else None
    segments, _ = model.transcribe(file_path, language=lang, beam_size=5)
    return " ".join(segment.text.strip() for segment in segments)
