import { useEffect, useRef, useState } from 'react'
import {
  View, Text, FlatList, TextInput, TouchableOpacity,
  StyleSheet, KeyboardAvoidingView, Platform, Alert
} from 'react-native'
import { useLocalSearchParams, useRouter } from 'expo-router'
import { Audio } from 'expo-av'
import { useChatStore, type Message } from '../../../src/store/chat'
import { useAuthStore } from '../../../src/store/auth'
import { AudioMessage } from '../../../src/components/AudioMessage'
import { VideoNoteMessage } from '../../../src/components/VideoNoteMessage'
import { api } from '../../../src/api/client'
import * as FileSystem from 'expo-file-system'

export default function ChatScreen() {
  const { id: chatId } = useLocalSearchParams<{ id: string }>()
  const router = useRouter()
  const { messages, loadMessages, sendText, joinChat } = useChatStore()
  const { user } = useAuthStore()
  const [text, setText] = useState('')
  const [recording, setRecording] = useState<Audio.Recording | null>(null)
  const [isRecording, setIsRecording] = useState(false)
  const flatRef = useRef<FlatList>(null)

  const chatMessages = messages[chatId] ?? []

  useEffect(() => {
    loadMessages(chatId)
    joinChat(chatId)
  }, [chatId])

  useEffect(() => {
    if (chatMessages.length > 0) {
      flatRef.current?.scrollToEnd({ animated: true })
    }
  }, [chatMessages.length])

  const handleSend = async () => {
    if (!text.trim()) return
    const t = text
    setText('')
    await sendText(chatId, t)
  }

  const startRecording = async () => {
    const { granted } = await Audio.requestPermissionsAsync()
    if (!granted) { Alert.alert('Permission needed', 'Microphone access required'); return }

    await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true })
    const { recording } = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY)
    setRecording(recording)
    setIsRecording(true)
  }

  const stopRecording = async () => {
    if (!recording) return
    setIsRecording(false)
    await recording.stopAndUnloadAsync()
    const uri = recording.getURI()
    setRecording(null)
    if (uri) await uploadAudio(uri)
  }

  const uploadAudio = async (uri: string) => {
    const formData = new FormData()
    formData.append('file', { uri, name: 'voice.m4a', type: 'audio/m4a' } as any)
    formData.append('type', 'audio')
    formData.append('sourceLang', user?.languageCode ?? 'en')
    await api.post(`/chats/${chatId}/media`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    loadMessages(chatId)
  }

  const renderMessage = ({ item }: { item: Message }) => {
    const isMe = item.senderId === user?.id
    const translation = item.translations?.find((t) => t.targetLang === user?.languageCode)

    const displayText = isMe
      ? item.originalText
      : (translation?.translatedText ?? item.originalText)

    return (
      <View style={[styles.msgRow, isMe && styles.msgRowMe]}>
        <View style={[styles.bubble, isMe ? styles.bubbleMe : styles.bubbleThem]}>
          {item.type === 'text' && (
            <>
              <Text style={styles.msgText}>{displayText}</Text>
              {!isMe && translation && item.originalLang !== user?.languageCode && (
                <Text style={styles.translatedBadge}>🌐 translated</Text>
              )}
              {!isMe && !translation?.isReady && (
                <Text style={styles.translatingBadge}>⏳ translating…</Text>
              )}
            </>
          )}
          {item.type === 'audio' && (
            <AudioMessage
              url={isMe ? item.mediaUrl! : (translation?.translatedMediaUrl ?? item.mediaUrl!)}
              isTranslated={!isMe && !!translation?.translatedMediaUrl}
              isReady={isMe || (translation?.isReady ?? false)}
              duration={item.mediaDuration}
            />
          )}
          {item.type === 'video_note' && (
            <VideoNoteMessage
              url={isMe ? item.mediaUrl! : (translation?.translatedMediaUrl ?? item.mediaUrl!)}
              isReady={isMe || (translation?.isReady ?? false)}
            />
          )}
        </View>
      </View>
    )
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={90}
    >
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back}>
          <Text style={styles.backIcon}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Chat</Text>
      </View>

      <FlatList
        ref={flatRef}
        data={chatMessages}
        keyExtractor={(m) => m.id}
        renderItem={renderMessage}
        contentContainerStyle={styles.messageList}
      />

      <View style={styles.inputRow}>
        <TextInput
          style={styles.input}
          value={text}
          onChangeText={setText}
          placeholder="Message…"
          placeholderTextColor="#444"
          multiline
          maxLength={4000}
        />
        {text.trim() ? (
          <TouchableOpacity style={styles.sendBtn} onPress={handleSend}>
            <Text style={styles.sendIcon}>↑</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={[styles.sendBtn, isRecording && styles.sendBtnRecording]}
            onPressIn={startRecording}
            onPressOut={stopRecording}
          >
            <Text style={styles.sendIcon}>{isRecording ? '⏹' : '🎤'}</Text>
          </TouchableOpacity>
        )}
      </View>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A0A0A' },
  header: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    paddingHorizontal: 16, paddingTop: 56, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: '#1A1A1A',
  },
  back: { padding: 4 },
  backIcon: { color: '#2AABEE', fontSize: 24 },
  headerTitle: { color: '#fff', fontSize: 18, fontWeight: '700' },
  messageList: { padding: 16, gap: 4 },
  msgRow: { flexDirection: 'row', marginVertical: 2 },
  msgRowMe: { justifyContent: 'flex-end' },
  bubble: { maxWidth: '80%', borderRadius: 18, padding: 12 },
  bubbleMe: { backgroundColor: '#2AABEE', borderBottomRightRadius: 4 },
  bubbleThem: { backgroundColor: '#1E1E1E', borderBottomLeftRadius: 4 },
  msgText: { color: '#fff', fontSize: 16, lineHeight: 22 },
  translatedBadge: { color: 'rgba(255,255,255,0.5)', fontSize: 11, marginTop: 4 },
  translatingBadge: { color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 4 },
  inputRow: {
    flexDirection: 'row', alignItems: 'flex-end', gap: 8,
    padding: 12, borderTopWidth: 1, borderTopColor: '#1A1A1A',
  },
  input: {
    flex: 1, backgroundColor: '#1A1A1A', borderRadius: 24,
    paddingHorizontal: 16, paddingVertical: 12,
    color: '#fff', fontSize: 16, maxHeight: 120,
  },
  sendBtn: {
    width: 44, height: 44, borderRadius: 22,
    backgroundColor: '#2AABEE', alignItems: 'center', justifyContent: 'center',
  },
  sendBtnRecording: { backgroundColor: '#EE2A2A' },
  sendIcon: { color: '#fff', fontSize: 18, fontWeight: '700' },
})
