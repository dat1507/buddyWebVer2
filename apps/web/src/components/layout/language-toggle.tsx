import type { SVGProps } from 'react'
import { useTranslation } from 'react-i18next'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

function UkFlag(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 60 30"
      className={cn('h-3.5 w-5 shrink-0 rounded-[2px] shadow-sm', props.className)}
      aria-hidden="true"
      {...props}
    >
      <clipPath id="uk-flag-clip">
        <rect width="60" height="30" />
      </clipPath>
      <g clipPath="url(#uk-flag-clip)">
        <rect width="60" height="30" fill="#012169" />
        <path d="M0 0 L60 30 M60 0 L0 30" stroke="#ffffff" strokeWidth="6" />
        <path d="M0 0 L60 30 M60 0 L0 30" stroke="#C8102E" strokeWidth="2" />
        <path d="M30 0 v30 M0 15 h60" stroke="#ffffff" strokeWidth="10" />
        <path d="M30 0 v30 M0 15 h60" stroke="#C8102E" strokeWidth="6" />
      </g>
    </svg>
  )
}

function GermanFlag(props: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 5 3"
      className={cn('h-3.5 w-5 shrink-0 rounded-[2px] shadow-sm', props.className)}
      aria-hidden="true"
      {...props}
    >
      <rect width="5" height="1" y="0" fill="#000000" />
      <rect width="5" height="1" y="1" fill="#DD0000" />
      <rect width="5" height="1" y="2" fill="#FFCE00" />
    </svg>
  )
}

interface LanguageToggleProps {
  variant?: 'desktop' | 'mobile'
  className?: string
  onToggle?: () => void
}

/**
 * LanguageToggle component
 *
 * Toggles between English (EN) and German (DE) with national flag icons.
 * Persists selected language to localStorage ('vgu-language') and updates
 * all active react-i18next translations and <html lang="...">.
 */
function LanguageToggle({ variant = 'desktop', className, onToggle }: LanguageToggleProps) {
  const { t, i18n } = useTranslation()
  const currentLang = i18n.resolvedLanguage?.startsWith('de') ? 'de' : 'en'
  const isGerman = currentLang === 'de'
  const languageCode = isGerman ? 'DE' : 'EN'
  const targetLanguage = t(isGerman ? 'nav.languageEnglish' : 'nav.languageGerman')
  const switchToLanguage = t('nav.switchToLanguage', { language: targetLanguage })
  const accessibleLabel = `${t('nav.currentLanguage', { language: languageCode })}. ${switchToLanguage}`

  const handleToggle = () => {
    const nextLang = isGerman ? 'en' : 'de'
    void i18n.changeLanguage(nextLang)
    try {
      localStorage.setItem('vgu-language', nextLang)
    } catch {
      // Ignore localStorage errors (e.g. private browsing restrictions)
    }
    onToggle?.()
  }

  if (variant === 'mobile') {
    return (
      <button
        type="button"
        onClick={handleToggle}
        className={cn(
          'flex w-full items-center justify-between rounded-lg bg-white/5 px-4 py-3 text-sm text-zinc-200 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500',
          className,
        )}
        aria-label={accessibleLabel}
      >
        <span className="flex items-center gap-2.5">
          {isGerman ? <GermanFlag /> : <UkFlag />}
          <span className="font-medium">{t('nav.language')}</span>
        </span>
        <span className="flex items-center gap-2 rounded-md bg-white/10 px-2.5 py-1 text-xs font-semibold text-orange-400">
          {languageCode}
          <span className="text-zinc-400">→ {isGerman ? 'EN' : 'DE'}</span>
        </span>
      </button>
    )
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      onClick={handleToggle}
      className={cn(
        'gap-2 text-zinc-300 hover:bg-white/10 hover:text-orange-400 focus-visible:ring-2 focus-visible:ring-orange-500',
        className,
      )}
      aria-label={accessibleLabel}
      title={switchToLanguage}
    >
      {isGerman ? <GermanFlag /> : <UkFlag />}
      <span className="font-semibold tracking-wide">{languageCode}</span>
    </Button>
  )
}

export { GermanFlag, LanguageToggle, UkFlag }
