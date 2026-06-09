import { useState } from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { Video, ResizeMode } from 'expo-av'
import { API_URL } from '../constants'

interface Props {
  url: string
  isReady: boolean
}

export function VideoNoteMessage({ url, isReady }: Props) {
  const [playing, setPlaying] = useState(false)
  const fullUrl = url.startsWith('http') ? url : `${API_URL.replace('/api', '')}${url}`

  if (!isReady) {
    return (
      <View style={styles.placeholder}>
        <ActivityIndicator size="large" color="#2AABEE" />
        <Text style={styles.label}>Translating…</Text>
      </View>
    )
  }

  return (
    <TouchableOpacity onPress={() => setPlaying((p) => !p)}>
      <View style={styles.circle}>
        <Video
          source={{ uri: fullUrl }}
          style={styles.video}
          resizeMode={ResizeMode.COVER}
          shouldPlay={playing}
          isLooping={false}
          isMuted={false}
        />
        {!playing && (
          <View style={styles.overlay}>
            <Text style={styles.playIcon}>▶</Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  )
}

const styles = StyleSheet.create({
  circle: { width: 180, height: 180, borderRadius: 90, overflow: 'hidden' },
  video: { width: 180, height: 180 },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0,0,0,0.3)',
    alignItems: 'center', justifyContent: 'center',
  },
  playIcon: { color: '#fff', fontSize: 40 },
  placeholder: {
    width: 180, height: 180, borderRadius: 90,
    backgroundColor: '#1A1A1A', alignItems: 'center', justifyContent: 'center', gap: 8,
  },
  label: { color: 'rgba(255,255,255,0.5)', fontSize: 12 },
})
