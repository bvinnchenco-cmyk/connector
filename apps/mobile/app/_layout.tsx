import { useEffect } from 'react'
import { Stack, useRouter } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import { getToken } from '../src/api/client'
import { useAuthStore } from '../src/store/auth'
import { api } from '../src/api/client'

export default function RootLayout() {
  const router = useRouter()
  const { setUser } = useAuthStore()

  useEffect(() => {
    getToken().then(async (token) => {
      if (!token) {
        router.replace('/(auth)/login')
        return
      }
      try {
        // validate token & get user
        const { data } = await api.get('/auth/me')
        setUser(data.user)
        router.replace('/(app)/chats')
      } catch {
        router.replace('/(auth)/login')
      }
    })
  }, [])

  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false }} />
    </>
  )
}
