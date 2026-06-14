import { ScrollView, View, Text, TouchableOpacity, StyleSheet, Image, Linking } from 'react-native'
import { useRouter } from 'expo-router'

const RESTAURANTS = [
  {
    rank: 1,
    name: 'Suay Restaurant',
    cuisine: 'Тайская · Fusion',
    rating: 4.9,
    price: '฿฿฿',
    description:
      'Один из самых известных ресторанов Пхукета. Шеф-повар Tammasak Chootong сочетает традиционные тайские вкусы с современными техниками. Идеально для романтического ужина.',
    address: 'Rat Uthit 200 Pi Rd, Kathu',
    tags: ['Лучший вид', 'Романтика', 'Авторская кухня'],
    emoji: '🌿',
    color: '#1A2E1A',
    accent: '#4CAF50',
  },
  {
    rank: 2,
    name: 'Kan Eang @ Pier',
    cuisine: 'Морепродукты · Тайская',
    rating: 4.8,
    price: '฿฿',
    description:
      'Легендарный ресторан на сваях прямо над морем в бухте Чалонг. Свежайшие морепродукты по традиционным тайским рецептам. Работает с 1974 года.',
    address: '44/1 Viset Rd, Chalong Bay',
    tags: ['На воде', 'Морепродукты', 'Закат'],
    emoji: '🦞',
    color: '#1A1A2E',
    accent: '#2AABEE',
  },
  {
    rank: 3,
    name: 'Blue Elephant',
    cuisine: 'Королевская тайская',
    rating: 4.8,
    price: '฿฿฿฿',
    description:
      'Ресторан высокой тайской кухни в колониальном особняке 1903 года. Рецепты из королевского дворца, приготовленные с использованием редких специй и трав.',
    address: '96 Krabi Rd, Phuket Town',
    tags: ['Исторический', 'Высокая кухня', 'Особняк'],
    emoji: '🐘',
    color: '#1E1A2E',
    accent: '#9C27B0',
  },
  {
    rank: 4,
    name: 'Acqua Restaurant',
    cuisine: 'Итальянская · Средиземноморская',
    rating: 4.7,
    price: '฿฿฿',
    description:
      'Лучший итальянский ресторан Пхукета по версии нескольких гидов. Шеф из Милана, свежая паста, великолепный выбор вин и панорамный вид на Андаманское море.',
    address: 'Millionaire\'s Mile, Kamala Beach',
    tags: ['Итальянская', 'Вид на море', 'Вино'],
    emoji: '🍝',
    color: '#2E1A1A',
    accent: '#F44336',
  },
  {
    rank: 5,
    name: 'Bampot Kitchen & Bar',
    cuisine: 'Тайская · Стрит-фуд Premium',
    rating: 4.6,
    price: '฿฿',
    description:
      'Модное местечко на Старом городе с открытой кухней и душевной атмосферой. Традиционные южно-тайские рецепты с современной подачей. Лучшие масаман карри в городе.',
    address: 'Thalang Rd, Phuket Old Town',
    tags: ['Стрит-фуд', 'Старый город', 'Атмосфера'],
    emoji: '🍛',
    color: '#2E2A1A',
    accent: '#FF9800',
  },
]

export default function GuideScreen() {
  const router = useRouter()

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.back}>
          <Text style={styles.backIcon}>←</Text>
        </TouchableOpacity>
        <View style={styles.headerMeta}>
          <Text style={styles.headerLabel}>ГИД</Text>
        </View>
      </View>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        <View style={styles.hero}>
          <Text style={styles.heroEmoji}>🌴</Text>
          <Text style={styles.heroTitle}>Топ-5 ресторанов{'\n'}Пхукета</Text>
          <Text style={styles.heroSubtitle}>
            Лучшие места острова — от уличной еды до высокой кухни
          </Text>
          <View style={styles.heroBadges}>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>🇹🇭 Тайланд</Text>
            </View>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>⭐ Проверено</Text>
            </View>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>📍 Пхукет</Text>
            </View>
          </View>
        </View>

        <View style={styles.divider} />

        {RESTAURANTS.map((r) => (
          <View key={r.rank} style={[styles.card, { backgroundColor: r.color, borderColor: r.accent + '40' }]}>
            <View style={styles.cardTop}>
              <View style={[styles.rankBadge, { backgroundColor: r.accent }]}>
                <Text style={styles.rankText}>#{r.rank}</Text>
              </View>
              <Text style={styles.cardEmoji}>{r.emoji}</Text>
            </View>

            <Text style={styles.cardName}>{r.name}</Text>
            <Text style={styles.cardCuisine}>{r.cuisine}</Text>

            <View style={styles.cardMeta}>
              <View style={styles.ratingRow}>
                <Text style={styles.star}>★</Text>
                <Text style={styles.ratingText}>{r.rating}</Text>
              </View>
              <Text style={[styles.price, { color: r.accent }]}>{r.price}</Text>
            </View>

            <Text style={styles.cardDescription}>{r.description}</Text>

            <View style={styles.tagRow}>
              {r.tags.map((tag) => (
                <View key={tag} style={[styles.tag, { borderColor: r.accent + '60' }]}>
                  <Text style={[styles.tagText, { color: r.accent }]}>{tag}</Text>
                </View>
              ))}
            </View>

            <View style={styles.addressRow}>
              <Text style={styles.addressIcon}>📍</Text>
              <Text style={styles.addressText}>{r.address}</Text>
            </View>
          </View>
        ))}

        <View style={styles.footer}>
          <Text style={styles.footerText}>
            Все рестораны проверены редакцией. Цены и режим работы могут меняться — уточняйте на месте.
          </Text>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0A0A0A' },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingTop: 56,
    paddingBottom: 12,
    gap: 12,
  },
  back: { padding: 4 },
  backIcon: { color: '#2AABEE', fontSize: 24 },
  headerMeta: { flex: 1 },
  headerLabel: {
    color: '#2AABEE',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 2,
  },

  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 40 },

  hero: {
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 28,
    alignItems: 'center',
    gap: 8,
  },
  heroEmoji: { fontSize: 48, marginBottom: 4 },
  heroTitle: {
    color: '#fff',
    fontSize: 30,
    fontWeight: '800',
    textAlign: 'center',
    lineHeight: 36,
  },
  heroSubtitle: {
    color: '#888',
    fontSize: 15,
    textAlign: 'center',
    lineHeight: 22,
    marginTop: 4,
  },
  heroBadges: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 12,
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  badge: {
    backgroundColor: '#1A1A1A',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  badgeText: { color: '#ccc', fontSize: 13 },

  divider: {
    height: 1,
    backgroundColor: '#1A1A1A',
    marginHorizontal: 20,
    marginBottom: 20,
  },

  card: {
    marginHorizontal: 16,
    marginBottom: 16,
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
  },
  cardTop: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  rankBadge: {
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  rankText: { color: '#fff', fontWeight: '800', fontSize: 13 },
  cardEmoji: { fontSize: 32 },

  cardName: {
    color: '#fff',
    fontSize: 20,
    fontWeight: '800',
    marginBottom: 2,
  },
  cardCuisine: {
    color: '#888',
    fontSize: 13,
    marginBottom: 10,
  },
  cardMeta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 12,
  },
  ratingRow: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  star: { color: '#FFD700', fontSize: 15 },
  ratingText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  price: { fontSize: 14, fontWeight: '700' },

  cardDescription: {
    color: '#bbb',
    fontSize: 14,
    lineHeight: 22,
    marginBottom: 14,
  },

  tagRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 14,
  },
  tag: {
    borderRadius: 8,
    borderWidth: 1,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  tagText: { fontSize: 12, fontWeight: '600' },

  addressRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
  },
  addressIcon: { fontSize: 13 },
  addressText: { color: '#666', fontSize: 13, flex: 1 },

  footer: {
    marginHorizontal: 20,
    marginTop: 12,
    padding: 16,
    backgroundColor: '#111',
    borderRadius: 12,
  },
  footerText: { color: '#555', fontSize: 12, lineHeight: 18, textAlign: 'center' },
})
