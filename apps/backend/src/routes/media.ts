import type { FastifyInstance } from 'fastify'
import { db } from '../db/index.js'
import { messages, messageTranslations, chatMembers } from '../db/schema.js'
import { eq } from 'drizzle-orm'
import { authMiddleware } from '../middleware/auth.js'
import { submitVoiceTranslation } from '../services/voice-translation.js'
import { users } from '../db/schema.js'
import path from 'path'
import fs from 'fs'
import { pipeline } from 'stream/promises'

const UPLOAD_DIR = process.env.UPLOAD_DIR ?? '/tmp/connector-uploads'

export async function mediaRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authMiddleware)

  // POST /chats/:chatId/media — upload audio/video_note message
  app.post<{ Params: { chatId: string } }>('/chats/:chatId/media', async (request, reply) => {
    const { chatId } = request.params

    const data = await request.file()
    if (!data) return reply.status(400).send({ error: 'No file uploaded' })

    const type = data.fields.type as any
    const duration = parseInt((data.fields.duration as any)?.value ?? '0')
    const sourceLang = (data.fields.sourceLang as any)?.value ?? request.userLang

    // save file locally (in prod: upload to Supabase Storage / Cloudflare R2)
    fs.mkdirSync(UPLOAD_DIR, { recursive: true })
    const ext = path.extname(data.filename) || (type?.value === 'audio' ? '.ogg' : '.mp4')
    const filename = `${Date.now()}-${request.userId}${ext}`
    const filepath = path.join(UPLOAD_DIR, filename)
    await pipeline(data.file, fs.createWriteStream(filepath))

    const mediaUrl = `/uploads/${filename}`

    // insert original message
    const [msg] = await db
      .insert(messages)
      .values({
        chatId,
        senderId: request.userId,
        type: type?.value ?? 'audio',
        originalLang: sourceLang,
        mediaUrl,
        mediaDuration: duration,
        status: 'sent',
      })
      .returning()

    // get sender's voice sample
    const sender = await db.query.users.findFirst({ where: eq(users.id, request.userId) })

    // get all unique languages in chat
    const members = await db.query.chatMembers.findMany({
      where: eq(chatMembers.chatId, chatId),
      with: { user: true },
    })

    const targetLangs = [
      ...new Set(
        members
          .map((m) => m.user.languageCode)
          .filter((l) => l !== sourceLang)
      ),
    ]

    // submit translation jobs (async — will be ready in seconds)
    for (const targetLang of targetLangs) {
      const [translation] = await db
        .insert(messageTranslations)
        .values({
          messageId: msg.id,
          targetLang,
          isReady: false,
        })
        .returning()

      // fire-and-forget: AI pipeline processes and updates DB when done
      submitVoiceTranslation({
        messageId: msg.id,
        mediaUrl: filepath,
        sourceLang,
        targetLang,
        voiceSampleUrl: sender?.voiceSampleUrl ?? undefined,
      }).then(async (job) => {
        // poll handled by AI pipeline webhook callback
      }).catch(console.error)
    }

    return reply.status(201).send({ message: msg, translating: targetLangs.length > 0 })
  })

  // POST /voice-sample — upload voice sample for voice cloning
  app.post('/voice-sample', async (request, reply) => {
    const data = await request.file()
    if (!data) return reply.status(400).send({ error: 'No file' })

    fs.mkdirSync(UPLOAD_DIR, { recursive: true })
    const filename = `voice-sample-${request.userId}.ogg`
    const filepath = path.join(UPLOAD_DIR, filename)
    await pipeline(data.file, fs.createWriteStream(filepath))

    await db
      .update(users)
      .set({ voiceSampleUrl: `/uploads/${filename}`, updatedAt: new Date() })
      .where(eq(users.id, request.userId))

    return reply.send({ ok: true, url: `/uploads/${filename}` })
  })

  // POST /ai/callback — AI pipeline notifies when translation is done
  app.post('/ai/callback', async (request, reply) => {
    const { messageId, targetLang, translatedMediaUrl, translatedText, success } = request.body as any

    await db
      .update(messageTranslations)
      .set({
        translatedMediaUrl,
        translatedText,
        isReady: success ?? true,
      })
      .where(
        eq(messageTranslations.messageId, messageId)
      )

    // notify WebSocket clients
    const msg = await db.query.messages.findFirst({ where: eq(messages.id, messageId) })
    if (msg) {
      app.websocketServer?.clients.forEach((client: any) => {
        if (client.chatId === msg.chatId && client.userLang === targetLang) {
          client.send(JSON.stringify({ type: 'translation_ready', messageId, targetLang }))
        }
      })
    }

    return reply.send({ ok: true })
  })
}
