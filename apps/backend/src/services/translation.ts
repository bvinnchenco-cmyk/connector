import { Translate } from '@google-cloud/translate/build/src/v2/index.js'

const translate = new Translate({
  key: process.env.GOOGLE_TRANSLATE_API_KEY,
})

export async function detectLanguage(text: string): Promise<string> {
  const [detection] = await translate.detect(text)
  return Array.isArray(detection) ? detection[0].language : detection.language
}

export async function translateText(text: string, targetLang: string, sourceLang?: string): Promise<string> {
  const [translation] = await translate.translate(text, {
    to: targetLang,
    from: sourceLang,
  })
  return translation
}

// Batch translate one text to multiple languages
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
