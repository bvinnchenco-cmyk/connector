import { pgTable, text, timestamp, uuid, integer, boolean, pgEnum } from 'drizzle-orm/pg-core'

export const messageTypeEnum = pgEnum('message_type', ['text', 'audio', 'video_note', 'image', 'file'])
export const messageStatusEnum = pgEnum('message_status', ['sending', 'sent', 'delivered', 'read'])

export const users = pgTable('users', {
  id: uuid('id').primaryKey().defaultRandom(),
  telegramId: text('telegram_id').unique(),
  username: text('username'),
  firstName: text('first_name').notNull(),
  lastName: text('last_name'),
  photoUrl: text('photo_url'),
  languageCode: text('language_code').notNull().default('en'),
  countryCode: text('country_code'),
  phone: text('phone'),
  // voice sample for cloning (30-sec audio stored in Supabase Storage)
  voiceSampleUrl: text('voice_sample_url'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
  updatedAt: timestamp('updated_at').defaultNow().notNull(),
})

export const chats = pgTable('chats', {
  id: uuid('id').primaryKey().defaultRandom(),
  isGroup: boolean('is_group').default(false).notNull(),
  name: text('name'),
  photoUrl: text('photo_url'),
  createdBy: uuid('created_by').references(() => users.id),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

export const chatMembers = pgTable('chat_members', {
  id: uuid('id').primaryKey().defaultRandom(),
  chatId: uuid('chat_id').references(() => chats.id, { onDelete: 'cascade' }).notNull(),
  userId: uuid('user_id').references(() => users.id, { onDelete: 'cascade' }).notNull(),
  joinedAt: timestamp('joined_at').defaultNow().notNull(),
})

export const messages = pgTable('messages', {
  id: uuid('id').primaryKey().defaultRandom(),
  chatId: uuid('chat_id').references(() => chats.id, { onDelete: 'cascade' }).notNull(),
  senderId: uuid('sender_id').references(() => users.id).notNull(),
  type: messageTypeEnum('type').notNull().default('text'),
  // original content
  originalText: text('original_text'),
  originalLang: text('original_lang'),
  // original media URL (audio/video)
  mediaUrl: text('media_url'),
  mediaDuration: integer('media_duration'),
  status: messageStatusEnum('status').default('sending').notNull(),
  replyToId: uuid('reply_to_id'),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})

// translated versions of each message per language
export const messageTranslations = pgTable('message_translations', {
  id: uuid('id').primaryKey().defaultRandom(),
  messageId: uuid('message_id').references(() => messages.id, { onDelete: 'cascade' }).notNull(),
  targetLang: text('target_lang').notNull(),
  translatedText: text('translated_text'),
  // for audio/video: translated audio in sender's cloned voice
  translatedMediaUrl: text('translated_media_url'),
  // processing state
  isReady: boolean('is_ready').default(false).notNull(),
  createdAt: timestamp('created_at').defaultNow().notNull(),
})
