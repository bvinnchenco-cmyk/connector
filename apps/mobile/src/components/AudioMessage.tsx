import { useState } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { Audio } from 'expo-av'
import { API_URL } from '../constants'

interface Props {
  url: string
  isTranslated: boolean
  isReady: boolean
  duration?: number | null
}

export function AudioMessage({ url, isTranslated, isReady, duration }: Props) {
  const [sound, setSound] = useState<Audio.Sound | null>(null)
  const [playing, setPlaying] = useState(false)

  const toggle = async () => {
    if (!isReady) return

    if (playing && sound) {
      await sound.pauseAsync()
      setPlaying(false)
      return
    }

    const fullUrl = url.startsWith('http') ? url : `${API_URL.replace('/api', '')}${url}`
    const { sound: s } = await Audio.Sound.createAsync({ uri: fullUrl })
    setSound(s)
    setPlaying(true)
    await s.playAsync()
    s.setOnPlaybackStatusUpdate((status) => {
      if (status.isLoaded && status.didJustFinish) {
        setPlaying(false)
        s.unloadAsync()
      }
    })
  }

  if (!isReady) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="small" color="#2AABEE" />
        <Text style={styles.label}>Translating voice…</Text>
      </View>
    )
  }

  return (
    <TouchableOpacity style={styles.container} onPress={toggle}>
      <Text style={styles.icon}>{playing ? '⏸' : '▶'}</Text>
      <View style={styles.waveform}>
        {Array.from({ length: 20 }).map((_, i) => (
          <View key={i} style={[styles.bar, { height: 6 + Math.random() * 18 }]} />
        ))}
      </View>
      <Text style={styles.duration}>{duration ? `${duration}s` : ''}</Text>
      {isTranslated && <Text style={styles.badge}>🌐</Text>}
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  container: { flexDirection: 'row', alignItems: 'center', gap: 8, minWidth: 180 },
  icon: { fontSize: 20, color: '#fff' },
  waveform: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 2, height: 32 },
  bar: { width: 3, backgroundColor: 'rgba(255,255,255,0.6)', borderRadius: 2 },
  duration: { color: 'rgba(255,255,255,0.6)', fontSize: 12 },
  label: { color: 'rgba(255,255,255,0.5)', fontSize: 12 },
  badge: { fontSize: 12 },
})
