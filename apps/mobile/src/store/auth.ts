import { create } from 'zustand'
import { api, saveToken, clearToken } from '../api/client'

interface User {
  id: string
  firstName: string
  lastName?: string
  username?: string
  photoUrl?: string
  languageCode: string
}

interface AuthStore {
  user: User | null
  token: string | null
  isLoading: boolean
  loginWithTelegram: (tgData: Record<string, any>) => Promise<void>
  logout: () => Promise<void>
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthStore>((set) => ({
  user: null,
  token: null,
  isLoading: false,

  loginWithTelegram: async (tgData) => {
    set({ isLoading: true })
    try {
      const { data } = await api.post('/auth/telegram', tgData)
      await saveToken(data.token)
      set({ user: data.user, token: data.token })
    } finally {
      set({ isLoading: false })
    }
  },

  logout: async () => {
    await clearToken()
    set({ user: null, token: null })
  },

  setUser: (user) => set({ user }),
}))
