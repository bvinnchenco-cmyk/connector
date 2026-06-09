import { create } from 'zustand'
import { api } from '../api/client'
import { WS_URL } from '../constants'
import { getToken } from '../api/client'

export interface Message {
  id: string
  chatId: string
  senderId: string
  type: 'text' | 'audio' | 'video_note'
  originalText?: string
  originalLang?: string
  mediaUrl?: string
  mediaDuration?: number
  status: string
  createdAt: string
  translations?: Array<{
    targetLang: string
    translatedText?: string
    translatedMediaUrl?: string
    isReady: boolean
  }>
}

export interface Chat {
  id: string
  isGroup: boolean
  name?: string
  members: Array<{ user: { id: string; firstName: string; photoUrl?: string } }>
}

interface ChatStore {
  chats: Chat[]
  messages: Record<string, Message[]>
  ws: WebSocket | null
  loadChats: () => Promise<void>
  loadMessages: (chatId: string) => Promise<void>
  sendText: (chatId: string, text: string) => Promise<void>
  connectWS: (userLang: string) => void
  joinChat: (chatId: string) => void
  addMessage: (msg: Message) => void
}

export const useChatStore = create<ChatStore>((set, get) => ({
  chats: [],
  messages: {},
  ws: null,

  loadChats: async () => {
    const { data } = await api.get('/chats')
    set({ chats: data.chats })
  },

  loadMessages: async (chatId) => {
    const { data } = await api.get(`/chats/${chatId}/messages`)
    set((s) => ({ messages: { ...s.messages, [chatId]: data.messages } }))
  },

  sendText: async (chatId, text) => {
    const { data } = await api.post(`/chats/${chatId}/messages`, { text })
    get().addMessage(data.message)
  },

  addMessage: (msg) => {
    set((s) => ({
      messages: {
        ...s.messages,
        [msg.chatId]: [...(s.messages[msg.chatId] ?? []), msg],
      },
    }))
  },

  connectWS: async (userLang) => {
    const token = await getToken()
    if (!token) return

    const ws = new WebSocket(`${WS_URL}?token=${token}`)
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'new_message') {
        // reload messages for that chat
        get().loadMessages(msg.chatId)
      }
      if (msg.type === 'translation_ready') {
        get().loadMessages(msg.chatId)
      }
    }
    set({ ws })
  },

  joinChat: (chatId) => {
    const { ws } = get()
    ws?.send(JSON.stringify({ type: 'join_chat', chatId }))
  },
}))
