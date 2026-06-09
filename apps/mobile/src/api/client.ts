import axios from 'axios'
import * as SecureStore from 'expo-secure-store'
import { API_URL } from '../constants'

export const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('auth_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export async function saveToken(token: string) {
  await SecureStore.setItemAsync('auth_token', token)
}

export async function clearToken() {
  await SecureStore.deleteItemAsync('auth_token')
}

export async function getToken() {
  return SecureStore.getItemAsync('auth_token')
}
