import { useState } from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet, ActivityIndicator,
  Alert, ScrollView
} from 'react-native'
import { useRouter } from 'expo-router'
import * as WebBrowser from 'expo-web-browser'
import { useAuthStore } from '../../src/store/auth'
import { TELEGRAM_BOT_NAME, LANGUAGES } from '../../src/constants'
import { API_URL } from '../../src/constants'

export default function LoginScreen() {
  const router = useRouter()
  const { loginWithTelegram, isLoading } = useAuthStore()
  const [step, setStep] = useState<'welcome' | 'lang'>('welcome')
  const [selectedLang, setSelectedLang] = useState('en')

  const handleTelegramLogin = async () => {
    // Open Telegram OAuth in browser
    // The bot must have domain set via @BotFather: /setdomain
    const url = `https://oauth.telegram.org/auth?bot_id=${TELEGRAM_BOT_NAME.replace('_bot','')}&origin=${encodeURIComponent(API_URL.replace('/api',''))}&return_to=${encodeURIComponent('connector://auth-callback')}`

    const result = await WebBrowser.openAuthSessionAsync(url, 'connector://auth-callback')

    if (result.type === 'success') {
      // parse tg data from URL fragment
      const params = new URLSearchParams(result.url.split('?')[1] ?? '')
      const tgData: Record<string, any> = {}
      params.forEach((v, k) => { tgData[k] = isNaN(Number(v)) ? v : Number(v) })
      tgData.language_code = selectedLang

      try {
        await loginWithTelegram(tgData)
        router.replace('/(app)/chats')
      } catch (e) {
        Alert.alert('Error', 'Login failed. Please try again.')
      }
    }
  }

  if (step === 'lang') {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Choose your language</Text>
        <Text style={styles.subtitle}>You'll receive all messages translated to this language</Text>
        <ScrollView style={styles.langList}>
          {LANGUAGES.map((lang) => (
            <TouchableOpacity
              key={lang.code}
              style={[styles.langItem, selectedLang === lang.code && styles.langSelected]}
              onPress={() => setSelectedLang(lang.code)}
            >
              <Text style={styles.langFlag}>{lang.flag}</Text>
              <Text style={styles.langName}>{lang.name}</Text>
              {selectedLang === lang.code && <Text style={styles.check}>✓</Text>}
            </TouchableOpacity>
          ))}
        </ScrollView>
        <TouchableOpacity style={styles.button} onPress={handleTelegramLogin} disabled={isLoading}>
          {isLoading
            ? <ActivityIndicator color="#fff" />
            : <Text style={styles.buttonText}>Continue with Telegram →</Text>
          }
        </TouchableOpacity>
      </View>
    )
  }

  return (
    <View style={styles.container}>
      <View style={styles.hero}>
        <Text style={styles.logo}>🌐</Text>
        <Text style={styles.appName}>Connector</Text>
        <Text style={styles.tagline}>Chat with anyone.{'\n'}In your language.</Text>
      </View>

      <View style={styles.features}>
        {[
          ['💬', 'Text messages auto-translated'],
          ['🎤', 'Voice messages in your language'],
          ['📹', 'Video notes with translated voice'],
          ['🗣️', 'Original speaker\'s voice preserved'],
        ].map(([icon, text]) => (
          <View key={text} style={styles.feature}>
            <Text style={styles.featureIcon}>{icon}</Text>
            <Text style={styles.featureText}>{text}</Text>
          </View>
        ))}
      </View>

      <TouchableOpacity style={styles.button} onPress={() => setStep('lang')}>
        <Text style={styles.buttonText}>Get Started</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A0A0A', padding: 24, paddingTop: 80 },
  hero: { alignItems: 'center', marginBottom: 48 },
  logo: { fontSize: 72, marginBottom: 12 },
  appName: { fontSize: 36, fontWeight: '800', color: '#fff', letterSpacing: -1 },
  tagline: { fontSize: 18, color: '#888', textAlign: 'center', marginTop: 8, lineHeight: 26 },
  features: { gap: 16, marginBottom: 48 },
  feature: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  featureIcon: { fontSize: 24, width: 36 },
  featureText: { color: '#ccc', fontSize: 16 },
  button: {
    backgroundColor: '#2AABEE', borderRadius: 16, paddingVertical: 18,
    alignItems: 'center', marginBottom: 24,
  },
  buttonText: { color: '#fff', fontSize: 17, fontWeight: '700' },
  title: { fontSize: 28, fontWeight: '800', color: '#fff', marginBottom: 8 },
  subtitle: { color: '#888', fontSize: 15, marginBottom: 24 },
  langList: { flex: 1, marginBottom: 16 },
  langItem: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    padding: 16, borderRadius: 12, marginBottom: 8, backgroundColor: '#1A1A1A',
  },
  langSelected: { backgroundColor: '#1A2A3A', borderWidth: 1, borderColor: '#2AABEE' },
  langFlag: { fontSize: 24 },
  langName: { color: '#fff', fontSize: 16, flex: 1 },
  check: { color: '#2AABEE', fontSize: 18, fontWeight: '700' },
})
