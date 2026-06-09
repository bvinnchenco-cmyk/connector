import axios from 'axios'

const AI_PIPELINE_URL = process.env.AI_PIPELINE_URL ?? 'http://localhost:8000'

export interface VoiceTranslationJob {
  jobId: string
  status: 'pending' | 'processing' | 'done' | 'error'
  outputUrl?: string
}

// Send audio/video to AI pipeline for transcription + translation + voice cloning
export async function submitVoiceTranslation(params: {
  messageId: string
  mediaUrl: string
  sourceLang: string
  targetLang: string
  voiceSampleUrl?: string // sender's voice sample for cloning
}): Promise<VoiceTranslationJob> {
  const { data } = await axios.post(`${AI_PIPELINE_URL}/jobs/voice-translate`, params)
  return data
}

export async function getJobStatus(jobId: string): Promise<VoiceTranslationJob> {
  const { data } = await axios.get(`${AI_PIPELINE_URL}/jobs/${jobId}`)
  return data
}

// Google Speech-to-Text (free tier: 60 min/month)
export async function transcribeAudio(audioUrl: string, languageCode: string): Promise<string> {
  const { data } = await axios.post(`${AI_PIPELINE_URL}/transcribe`, {
    audioUrl,
    languageCode,
  })
  return data.transcript
}
