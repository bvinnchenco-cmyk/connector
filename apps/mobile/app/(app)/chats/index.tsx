import { useEffect } from 'react'
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Image } from 'react-native'
import { useRouter } from 'expo-router'
import { useChatStore, type Chat } from '../../../src/store/chat'
import { useAuthStore } from '../../../src/store/auth'

export default function ChatsScreen() {
  const router = useRouter()
  const { chats, loadChats, connectWS } = useChatStore()
  const { user } = useAuthStore()

  useEffect(() => {
    loadChats()
    if (user) connectWS(user.languageCode)
  }, [])

  const getChatName = (chat: Chat) => {
    if (chat.name) return chat.name
    const other = chat.members?.find((m) => m.user.id !== user?.id)
    return other?.user.firstName ?? 'Chat'
  }

  const getChatPhoto = (chat: Chat) => {
    const other = chat.members?.find((m) => m.user.id !== user?.id)
    return other?.user.photoUrl
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Messages</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={() => router.push('/(app)/guide')} style={styles.guideBtn}>
            <Text style={styles.guideBtnText}>🌴 Гид</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => router.push('/(app)/search')} style={styles.newChat}>
            <Text style={styles.newChatIcon}>✏️</Text>
          </TouchableOpacity>
        </View>
      </View>

      {chats.length === 0 ? (
        <View style={styles.empty}>
          <Text style={styles.emptyIcon}>💬</Text>
          <Text style={styles.emptyTitle}>No messages yet</Text>
          <Text style={styles.emptyText}>Find people to chat with</Text>
          <TouchableOpacity style={styles.findButton} onPress={() => router.push('/(app)/search')}>
            <Text style={styles.findButtonText}>Find people</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={chats}
          keyExtractor={(c) => c.id}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={styles.chatItem}
              onPress={() => router.push(`/(app)/chats/${item.id}`)}
            >
              <View style={styles.avatar}>
                {getChatPhoto(item)
                  ? <Image source={{ uri: getChatPhoto(item) }} style={styles.avatarImg} />
                  : <Text style={styles.avatarText}>{getChatName(item)[0]?.toUpperCase()}</Text>
                }
              </View>
              <View style={styles.chatInfo}>
                <Text style={styles.chatName}>{getChatName(item)}</Text>
                <Text style={styles.chatPreview}>Tap to open</Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A0A0A' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 20, paddingTop: 60, paddingBottom: 16,
  },
  headerTitle: { color: '#fff', fontSize: 28, fontWeight: '800' },
  headerActions: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  guideBtn: {
    backgroundColor: '#1A1A1A',
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  guideBtnText: { color: '#fff', fontSize: 13, fontWeight: '600' },
  newChat: { padding: 8 },
  newChatIcon: { fontSize: 22 },
  chatItem: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12 },
  avatar: {
    width: 52, height: 52, borderRadius: 26,
    backgroundColor: '#2AABEE', alignItems: 'center', justifyContent: 'center',
  },
  avatarImg: { width: 52, height: 52, borderRadius: 26 },
  avatarText: { color: '#fff', fontSize: 20, fontWeight: '700' },
  chatInfo: { flex: 1 },
  chatName: { color: '#fff', fontSize: 16, fontWeight: '600' },
  chatPreview: { color: '#666', fontSize: 14, marginTop: 2 },
  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 8 },
  emptyIcon: { fontSize: 64 },
  emptyTitle: { color: '#fff', fontSize: 20, fontWeight: '700', marginTop: 8 },
  emptyText: { color: '#666', fontSize: 15 },
  findButton: {
    marginTop: 16, backgroundColor: '#2AABEE',
    paddingHorizontal: 24, paddingVertical: 14, borderRadius: 12,
  },
  findButtonText: { color: '#fff', fontWeight: '700', fontSize: 16 },
})
