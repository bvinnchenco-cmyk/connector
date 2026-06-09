import { useState } from 'react'
import { View, Text, TextInput, FlatList, TouchableOpacity, StyleSheet, Image } from 'react-native'
import { useRouter } from 'expo-router'
import { api } from '../../src/api/client'

export default function SearchScreen() {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])

  const search = async (q: string) => {
    setQuery(q)
    if (q.length < 2) { setResults([]); return }
    const { data } = await api.get(`/users/search?q=${q}`)
    setResults(data.users)
  }

  const openChat = async (userId: string) => {
    const { data } = await api.post('/chats/direct', { targetUserId: userId })
    router.replace(`/(app)/chats/${data.chat.id}`)
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()}>
          <Text style={styles.cancel}>Cancel</Text>
        </TouchableOpacity>
        <TextInput
          style={styles.search}
          value={query}
          onChangeText={search}
          placeholder="Search by username…"
          placeholderTextColor="#444"
          autoFocus
        />
      </View>

      <FlatList
        data={results}
        keyExtractor={(u) => u.id}
        renderItem={({ item }) => (
          <TouchableOpacity style={styles.userItem} onPress={() => openChat(item.id)}>
            <View style={styles.avatar}>
              {item.photoUrl
                ? <Image source={{ uri: item.photoUrl }} style={styles.avatarImg} />
                : <Text style={styles.avatarText}>{item.firstName[0]}</Text>
              }
            </View>
            <View>
              <Text style={styles.name}>{item.firstName} {item.lastName}</Text>
              {item.username && <Text style={styles.username}>@{item.username}</Text>}
            </View>
          </TouchableOpacity>
        )}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A0A0A', paddingTop: 56 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16 },
  cancel: { color: '#2AABEE', fontSize: 16 },
  search: {
    flex: 1, backgroundColor: '#1A1A1A', borderRadius: 12,
    padding: 12, color: '#fff', fontSize: 16,
  },
  userItem: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 16 },
  avatar: {
    width: 48, height: 48, borderRadius: 24,
    backgroundColor: '#2AABEE', alignItems: 'center', justifyContent: 'center',
  },
  avatarImg: { width: 48, height: 48, borderRadius: 24 },
  avatarText: { color: '#fff', fontSize: 18, fontWeight: '700' },
  name: { color: '#fff', fontSize: 16, fontWeight: '600' },
  username: { color: '#666', fontSize: 14 },
})
