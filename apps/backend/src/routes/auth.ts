import type { FastifyInstance } from 'fastify'
import jwt from 'jsonwebtoken'
import { z } from 'zod'
import { db } from '../db/index.js'
import { users } from '../db/schema.js'
import { verifyTelegramAuth, type TelegramAuthData, authMiddleware } from '../middleware/auth.js'
import { eq } from 'drizzle-orm'

const telegramAuthSchema = z.object({
  id: z.number(),
  first_name: z.string(),
  last_name: z.string().optional(),
  username: z.string().optional(),
  photo_url: z.string().optional(),
  auth_date: z.number(),
  hash: z.string(),
  language_code: z.string().optional(),
})

export async function authRoutes(app: FastifyInstance) {
  // POST /auth/telegram — receive Telegram Login Widget data
  app.post('/auth/telegram', async (request, reply) => {
    const parseResult = telegramAuthSchema.safeParse(request.body)
    if (!parseResult.success) {
      return reply.status(400).send({ error: 'Invalid data' })
    }

    const tgData = parseResult.data as TelegramAuthData

    if (!verifyTelegramAuth(tgData)) {
      return reply.status(401).send({ error: 'Telegram auth verification failed' })
    }

    const telegramId = String(tgData.id)

    // upsert user
    let user = await db.query.users.findFirst({
      where: eq(users.telegramId, telegramId),
    })

    if (!user) {
      const [created] = await db
        .insert(users)
        .values({
          telegramId,
          firstName: tgData.first_name,
          lastName: tgData.last_name,
          username: tgData.username,
          photoUrl: tgData.photo_url,
          languageCode: tgData.language_code ?? 'en',
        })
        .returning()
      user = created
    }

    const token = jwt.sign(
      { userId: user.id, lang: user.languageCode },
      process.env.JWT_SECRET!,
      { expiresIn: '30d' }
    )

    return reply.send({ token, user })
  })

  // GET /auth/me — get current user (validates JWT)
  app.get('/auth/me', { preHandler: authMiddleware }, async (request, reply) => {
    const user = await db.query.users.findFirst({ where: eq(users.id, request.userId) })
    if (!user) return reply.status(404).send({ error: 'User not found' })
    return reply.send({ user })
  })

  // PATCH /auth/language — update user's preferred language
  app.patch('/auth/language', async (request, reply) => {
    const { lang } = request.body as { lang: string }
    if (!lang) return reply.status(400).send({ error: 'lang required' })

    const [updated] = await db
      .update(users)
      .set({ languageCode: lang, updatedAt: new Date() })
      .where(eq(users.id, request.userId))
      .returning()

    return reply.send({ user: updated })
  })
}
