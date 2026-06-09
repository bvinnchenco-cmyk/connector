import type { FastifyRequest, FastifyReply } from 'fastify'
import jwt from 'jsonwebtoken'
import crypto from 'crypto'

export interface TelegramAuthData {
  id: number
  first_name: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
  language_code?: string
}

export function verifyTelegramAuth(data: TelegramAuthData): boolean {
  const botToken = process.env.TELEGRAM_BOT_TOKEN!
  const secretKey = crypto.createHash('sha256').update(botToken).digest()

  const { hash, ...rest } = data
  const checkString = Object.keys(rest)
    .sort()
    .map((k) => `${k}=${rest[k as keyof typeof rest]}`)
    .join('\n')

  const hmac = crypto.createHmac('sha256', secretKey).update(checkString).digest('hex')

  // auth_date must be within 1 day
  const authAge = Math.floor(Date.now() / 1000) - data.auth_date
  if (authAge > 86400) return false

  return hmac === hash
}

export async function authMiddleware(request: FastifyRequest, reply: FastifyReply) {
  const authHeader = request.headers.authorization
  if (!authHeader?.startsWith('Bearer ')) {
    return reply.status(401).send({ error: 'Unauthorized' })
  }

  const token = authHeader.slice(7)
  try {
    const payload = jwt.verify(token, process.env.JWT_SECRET!) as { userId: string; lang: string }
    request.userId = payload.userId
    request.userLang = payload.lang
  } catch {
    return reply.status(401).send({ error: 'Invalid token' })
  }
}

declare module 'fastify' {
  interface FastifyRequest {
    userId: string
    userLang: string
  }
}
