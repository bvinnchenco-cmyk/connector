import type { FastifyInstance } from 'fastify'
import { db } from '../db/index.js'
import { messages, messageTranslations, chatMembers, users } from '../db/schema.js'
import { eq, and, inArray } from 'drizzle-orm'
import { translateToMany, detectLanguage } from '../services/translation.js'
import { submitVoiceTranslation } from '../services/voice-translation.js'
import { authMiddleware } from '../middleware/auth.js'

export async function messageRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authMiddleware)

  // GET /chats/:chatId/messages
  app.get<{ Params: { chatId: string } }>('/chats/:chatId/messages', async (request, reply) => {
    const { chatId } = request.params
    const userLang = request.userLang

    const msgs = await db.query.messages.findMany({
      where: eq(messages.chatId, chatId),
      with: {
        translations: {
          where: eq(messageTranslations.targetLang, userLang),
        },
      },
      orderBy: (m, { asc }) => [asc(m.createdAt)],
      limit: 50,
    })

    return reply.send({ messages: msgs })
  })

  // POST /chats/:chatId/messages — send text message
  app.post<{ Params: { chatId: string } }>('/chats/:chatId/messages', async (request, reply) => {
    const { chatId } = request.params
    const { text } = request.body as { text: string }

    if (!text?.trim()) return reply.status(400).send({ error: 'text required' })

    // detect language of message
    const detectedLang = await detectLanguage(text)

    // insert message
    const [msg] = await db
      .insert(messages)
      .values({
        chatId,
        senderId: request.userId,
        type: 'text',
        originalText: text,
        originalLang: detectedLang,
        status: 'sent',
      })
      .returning()

    // find all unique languages in this chat (except sender's)
    const members = await db.query.chatMembers.findMany({
      where: eq(chatMembers.chatId, chatId),
      with: { user: true },
    })

    const targetLangs = [
      ...new Set(
        members
          .map((m) => m.user.languageCode)
          .filter((l) => l !== detectedLang)
      ),
    ]

    // translate to all needed languages in parallel
    if (targetLangs.length > 0) {
      const translations = await translateToMany(text, targetLangs, detectedLang)

      await db.insert(messageTranslations).values(
        Object.entries(translations).map(([lang, translated]) => ({
          messageId: msg.id,
          targetLang: lang,
          translatedText: translated,
          isReady: true,
        }))
      )
    }

    // notify via WebSocket (broadcast to chat room)
    app.websocketServer?.clients.forEach((client: any) => {
      if (client.chatId === chatId && client.userId !== request.userId) {
        client.send(JSON.stringify({ type: 'new_message', messageId: msg.id, chatId }))
      }
    })

    return reply.status(201).send({ message: msg })
  })
}
