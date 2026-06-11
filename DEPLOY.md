# Деплой Connector в облако

## Стек
- **Supabase** — PostgreSQL + Storage (бесплатно)
- **Railway** — Backend + AI Pipeline + LibreTranslate (бесплатно $5/мес)

---

## Шаг 1 — Supabase (база данных)

1. Зайди на [supabase.com](https://supabase.com) → **Start your project**
2. Войди через GitHub
3. **New project** → придумай название (например `connector`) → задай пароль БД → выбери регион **Europe (Frankfurt)**
4. Подожди ~2 минуты пока создаётся
5. Зайди в **Settings → Database → Connection string → URI**
6. Скопируй строку — она выглядит так:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxx.supabase.co:5432/postgres
   ```
   Это твой `DATABASE_URL`

---

## Шаг 2 — Railway (сервисы)

1. Зайди на [railway.app](https://railway.app) → **Login with GitHub**
2. **New Project → Deploy from GitHub repo**
3. Выбери репозиторий `connector`

### Создай сервис Backend:
1. В проекте нажми **+ New Service → GitHub Repo**
2. Выбери репозиторий → **Root Directory**: `apps/backend`
3. Railway автоматически определит Dockerfile

**Environment Variables** (нажми Variables → Raw Editor, вставь всё):
```env
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
JWT_SECRET=сгенерируй_случайную_строку_32_символа
TELEGRAM_BOT_TOKEN=8514195685:AAEf4A_lu2piSMehSBf079ARfEOVFEFvknQ
LIBRETRANSLATE_URL=https://[libretranslate-service].railway.app
AI_PIPELINE_URL=https://[ai-pipeline-service].railway.app
NODE_ENV=production
PORT=3000
UPLOAD_DIR=/tmp/uploads
```

### Создай сервис LibreTranslate:
1. **+ New Service → Docker Image**
2. Image: `libretranslate/libretranslate`
3. **Environment Variables:**
```env
LT_LOAD_ONLY=en,ru,fr,de,es,it,zh,ja,ko,ar,pt,tr,th,vi
PORT=5000
```

### Создай сервис AI Pipeline:
1. **+ New Service → GitHub Repo**
2. Root Directory: `apps/ai-pipeline`
3. **Environment Variables:**
```env
LIBRETRANSLATE_URL=https://[libretranslate-service].railway.app
BACKEND_URL=https://[backend-service].railway.app
PORT=8000
```

---

## Шаг 3 — Настрой Telegram бота

Чтобы Telegram Login Widget работал, нужно установить домен бота:

1. Открой [@BotFather](https://t.me/BotFather)
2. Напиши `/setdomain`
3. Выбери `@Connector_AppBot`
4. Введи домен backend: `https://[backend].railway.app`

---

## Шаг 4 — Применить схему БД

После деплоя backend, открой Railway → Backend → **Shell** и выполни:
```bash
npm run db:push
```

---

## Шаг 5 — Мобильное приложение

Создай файл `apps/mobile/.env`:
```env
EXPO_PUBLIC_API_URL=https://[backend].railway.app/api
EXPO_PUBLIC_WS_URL=wss://[backend].railway.app/ws
EXPO_PUBLIC_TELEGRAM_BOT_NAME=Connector_AppBot
```

Запусти на телефоне через Expo Go:
```bash
cd apps/mobile
npm install
npx expo start
```
Сканируй QR-код приложением **Expo Go** (iOS/Android).

---

## Итог (всё бесплатно)

| Сервис | Платформа | Стоимость |
|--------|-----------|-----------|
| PostgreSQL | Supabase | Бесплатно |
| Backend API | Railway | ~$1-2/мес |
| LibreTranslate | Railway | ~$1/мес |
| AI Pipeline | Railway | ~$2/мес |
| **Итого** | | **в пределах $5 free credit** |
