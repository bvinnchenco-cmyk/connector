import type { FastifyInstance } from 'fastify'
import { db } from '../db/index.js'
import { chats, chatMembers, users } from '../db/schema.js'
import { eq, and } from 'drizzle-orm'
import { authMiddleware } from '../middleware/auth.js'

export async function chatRoutes(app: FastifyInstance) {
  app.addHook('preHandler', authMiddleware)

  // GET /chats — my chats
  app.get('/chats', async (request, reply) => {
    const myChats = await db.query.chatMembers.findMany({
      where: eq(chatMembers.userId, request.userId),
      with: {
        chat: {
          with: {
            members: { with: { user: true } },
          },
        },
      },
    })
    return reply.send({ chats: myChats.map((m) => m.chat) })
  })

  // POST /chats/direct — open or create direct chat with a user
  app.post('/chats/direct', async (request, reply) => {
    const { targetUserId } = request.body as { targetUserId: string }

    // check if direct chat already exists between these two
    const existing = await db
      .select({ chatId: chatMembers.chatId })
      .from(chatMembers)
      .where(eq(chatMembers.userId, request.userId))

    // simple approach: create new direct chat
    const [chat] = await db.insert(chats).values({ createdBy: request.userId, isGroup: false }).returning()

    await db.insert(chatMembers).values([
      { chatId: chat.id, userId: request.userId },
      { chatId: chat.id, userId: targetUserId },
    ])

    return reply.status(201).send({ chat })
  })

  // GET /users/search?q=
  app.get('/users/search', async (request, reply) => {
    const q = (request.query as any).q as string
    if (!q) return reply.status(400).send({ error: 'q required' })

    const results = await db.query.users.findMany({
      where: (u, { ilike }) => ilike(u.username, `%${q}%`),
      limit: 20,
    })
    return reply.send({ users: results })
  })
}
