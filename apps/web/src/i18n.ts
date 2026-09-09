import i18n from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import { initReactI18next } from 'react-i18next'

import deCommon from './locales/de/common.json'
import enCommon from './locales/en/common.json'

const fallbackLanguage = 'en'

function updateDocumentLanguage(language: string) {
  document.documentElement.lang = language.split('-')[0] || fallbackLanguage
}

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: { common: deCommon },
      en: { common: enCommon },
    },
    supportedLngs: ['en', 'de'],
    fallbackLng: fallbackLanguage,
    load: 'languageOnly',
    ns: ['common'],
    defaultNS: 'common',
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'vgu-language',
    },
    interpolation: {
      escapeValue: false,
    },
  })
  .then(() => updateDocumentLanguage(i18n.resolvedLanguage ?? fallbackLanguage))

i18n.on('languageChanged', updateDocumentLanguage)

export default i18n
