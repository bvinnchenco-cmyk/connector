import axios from 'axios'

// Free translation providers — no API keys needed
// Priority: LibreTranslate (self-hosted) → MyMemory (free public API)

const LIBRETRANSLATE_URL = process.env.LIBRETRANSLATE_URL ?? 'http://libretranslate:5000'
const MYMEMORY_URL = 'https://api.mymemory.translated.net/get'

// LibreTranslate uses different lang codes for some languages
const LIBRE_LANG_MAP: Record<string, string> = {
  zh: 'zh',
  'zh-cn': 'zh',
  'zh-tw': 'zh',
}
function toLibreLang(code: string) {
  const base = code.split('-')[0].toLowerCase()
  return LIBRE_LANG_MAP[base] ?? base
}

async function translateWithLibre(text: string, target: string, source?: string): Promise<string> {
  const { data } = await axios.post(
    `${LIBRETRANSLATE_URL}/translate`,
    {
      q: text,
      source: source ? toLibreLang(source) : 'auto',
      target: toLibreLang(target),
      format: 'text',
    },
    { timeout: 10_000 }
  )
  return data.translatedText as string
}

async function detectWithLibre(text: string): Promise<string> {
  const { data } = await axios.post(
    `${LIBRETRANSLATE_URL}/detect`,
    { q: text },
    { timeout: 5_000 }
  )
  return (data[0]?.language as string) ?? 'en'
}

async function translateWithMyMemory(text: string, target: string, source?: string): Promise<string> {
  const langPair = `${source ?? 'auto'}|${target}`
  const { data } = await axios.get(MYMEMORY_URL, {
    params: { q: text, langpair: langPair },
    timeout: 10_000,
  })
  if (data.responseStatus === 200) return data.responseData.translatedText as string
  throw new Error(`MyMemory error: ${data.responseStatus}`)
}

export async function detectLanguage(text: string): Promise<string> {
  try {
    return await detectWithLibre(text)
  } catch {
    // fallback: return 'en' — we'll still translate to all langs
    return 'en'
  }
}

export async function translateText(text: string, targetLang: string, sourceLang?: string): Promise<string> {
  // skip if same language
  if (sourceLang && sourceLang.split('-')[0] === targetLang.split('-')[0]) return text

  // 1. try LibreTranslate (self-hosted, unlimited)
  try {
    return await translateWithLibre(text, targetLang, sourceLang)
  } catch {
    // 2. fallback to MyMemory (free public, 5k chars/day)
    try {
      return await translateWithMyMemory(text, targetLang, sourceLang)
    } catch (e) {
      console.error('All translation providers failed:', e)
      return text // return original if all fail
    }
  }
}

export async function translateToMany(
  text: string,
  targetLangs: string[],
  sourceLang?: string
): Promise<Record<string, string>> {
  const results: Record<string, string> = {}
  await Promise.all(
    targetLangs.map(async (lang) => {
      results[lang] = await translateText(text, lang, sourceLang)
    })
  )
  return results
}
