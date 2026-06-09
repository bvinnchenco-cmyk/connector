import 'dotenv/config'
import Fastify from 'fastify'
import fastifyWebsocket from '@fastify/websocket'
import fastifyCors from '@fastify/cors'
import fastifyMultipart from '@fastify/multipart'
import fastifyStatic from '@fastify/static'
import path from 'path'
import { authRoutes } from './routes/auth.js'
import { chatRoutes } from './routes/chats.js'
import { messageRoutes } from './routes/messages.js'
import { mediaRoutes } from './routes/media.js'
import { authMiddleware } from './middleware/auth.js'

const app = Fastify({ logger: { level: 'info' } })

await app.register(fastifyCors, { origin: true, credentials: true })
await app.register(fastifyWebsocket)
await app.register(fastifyMultipart, { limits: { fileSize: 100 * 1024 * 1024 } }) // 100MB
await app.register(fastifyStatic, {
  root: process.env.UPLOAD_DIR ?? '/tmp/connector-uploads',
  prefix: '/uploads/',
})

// REST routes
await app.register(authRoutes, { prefix: '/api' })
await app.register(chatRoutes, { prefix: '/api' })
await app.register(messageRoutes, { prefix: '/api' })
await app.register(mediaRoutes, { prefix: '/api' })

// WebSocket — real-time messaging
app.get('/ws', { websocket: true }, (socket, request) => {
  const token = (request.query as any).token as string

  // verify JWT inline
  import('jsonwebtoken').then(({ default: jwt }) => {
    try {
      const payload = jwt.verify(token, process.env.JWT_SECRET!) as { userId: string; lang: string }
      ;(socket as any).userId = payload.userId
      ;(socket as any).userLang = payload.lang
    } catch {
      socket.close(1008, 'Invalid token')
      return
    }

    socket.on('message', (rawMsg: Buffer) => {
      try {
        const msg = JSON.parse(rawMsg.toString())
        // client sends { type: 'join_chat', chatId }
        if (msg.type === 'join_chat') {
          ;(socket as any).chatId = msg.chatId
        }
      } catch {}
    })

    socket.on('close', () => {})
  })
})

app.get('/health', async () => ({ ok: true, ts: Date.now() }))

const port = parseInt(process.env.PORT ?? '3000')
await app.listen({ port, host: '0.0.0.0' })
console.log(`Connector backend running on port ${port}`)
