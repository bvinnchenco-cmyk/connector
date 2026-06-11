"""
Connector AI Pipeline
Handles: transcription → translation → voice cloning TTS → output audio
"""
import os
import uuid
import asyncio
import httpx
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from pipeline.transcribe import transcribe_audio
from pipeline.translate import translate_text
from pipeline.synthesize import synthesize_voice
from pipeline.video import replace_audio_in_video

app = FastAPI(title="Connector AI Pipeline")

JOBS: dict[str, dict] = {}


class Settings(BaseSettings):
    upload_dir: str = "/tmp/connector-uploads"
    output_dir: str = "/tmp/connector-outputs"
    backend_url: str = "http://localhost:3000"
    libretranslate_url: str = "http://libretranslate:5000"
    port: int = 8000

    class Config:
        env_file = ".env"


settings = Settings()
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)


class VoiceTranslateRequest(BaseModel):
    messageId: str
    mediaUrl: str
    sourceLang: str
    targetLang: str
    voiceSampleUrl: str | None = None


class TranscribeRequest(BaseModel):
    audioUrl: str
    languageCode: str


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/jobs/voice-translate")
async def voice_translate(req: VoiceTranslateRequest, background: BackgroundTasks):
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "messageId": req.messageId}
    background.add_task(run_voice_translation, job_id, req)
    return {"jobId": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    return JOBS.get(job_id, {"status": "not_found"})


@app.post("/transcribe")
async def transcribe(req: TranscribeRequest):
    transcript = await transcribe_audio(req.audioUrl, req.languageCode)
    return {"transcript": transcript}


async def run_voice_translation(job_id: str, req: VoiceTranslateRequest):
    try:
        JOBS[job_id]["status"] = "processing"

        media_path = req.mediaUrl
        is_video = media_path.endswith(('.mp4', '.mov', '.webm'))

        # 1. Transcribe (faster-whisper, free local)
        transcript = await transcribe_audio(media_path, req.sourceLang)

        # 2. Translate (LibreTranslate → Google unofficial → MyMemory)
        translated_text = await translate_text(transcript, req.targetLang, req.sourceLang)

        # 3. Synthesize in sender's voice (XTTS v2, free local)
        output_audio_path = os.path.join(
            settings.output_dir,
            f"{req.messageId}_{req.targetLang}.wav"
        )
        await synthesize_voice(
            text=translated_text,
            target_lang=req.targetLang,
            voice_sample_path=req.voiceSampleUrl,
            output_path=output_audio_path,
        )

        output_url = f"/outputs/{os.path.basename(output_audio_path)}"

        # 4. For video notes: replace audio track with translated audio
        if is_video:
            output_video_path = output_audio_path.replace('.wav', '.mp4')
            await replace_audio_in_video(media_path, output_audio_path, output_video_path)
            output_url = f"/outputs/{os.path.basename(output_video_path)}"

        JOBS[job_id] = {"status": "done", "outputUrl": output_url}

        # 5. Notify backend
        async with httpx.AsyncClient() as client:
            await client.post(f"{settings.backend_url}/api/ai/callback", json={
                "messageId": req.messageId,
                "targetLang": req.targetLang,
                "translatedText": translated_text,
                "translatedMediaUrl": output_url,
                "success": True,
            })

    except Exception as e:
        JOBS[job_id] = {"status": "error", "error": str(e)}
        async with httpx.AsyncClient() as client:
            await client.post(f"{settings.backend_url}/api/ai/callback", json={
                "messageId": req.messageId,
                "targetLang": req.targetLang,
                "success": False,
            })
