import type { SVGProps } from 'react'
import { ExternalLink } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import vguBuddyLogo from '@/assets/vgu-buddy-logo.png'

function FacebookIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3V2Z" />
    </svg>
  )
}

function InstagramIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" {...props}>
      <rect width="18" height="18" x="3" y="3" rx="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="1" fill="currentColor" stroke="none" />
    </svg>
  )
}

const quickLinks = [
  { href: '/#home', translationKey: 'nav.home' },
  { href: '/#about', translationKey: 'nav.about' },
  { href: '/#features', translationKey: 'nav.features' },
  { href: '/#community', translationKey: 'nav.community' },
] as const

const socialLinks = [
  {
    href: 'https://www.facebook.com/VGUBuddyProgram',
    label: 'Facebook',
    Icon: FacebookIcon,
  },
  {
    href: 'https://www.instagram.com/buddyprogram_vgu/',
    label: 'Instagram',
    Icon: InstagramIcon,
  },
] as const

function Footer() {
  const { t } = useTranslation()
  const currentYear = new Date().getFullYear()

  return (
    <footer id="contact" className="border-t border-white/10 bg-zinc-950">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr] lg:gap-12">
          <div>
            <a
              href="/#home"
              className="inline-flex items-center gap-3 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
              aria-label="VGU Buddy Program"
            >
              <img src={vguBuddyLogo} alt="" className="h-12 w-12 rounded-xl object-cover" />
              <span className="text-xl font-bold text-white">VGU Buddy</span>
            </a>

            <p className="mt-5 max-w-xl text-base leading-7 text-zinc-400">
              {t('footer.description')}
            </p>

            <div className="mt-6 flex gap-3">
              {socialLinks.map(({ href, label, Icon }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={label}
                  className="flex size-11 items-center justify-center rounded-lg border border-white/10 bg-black text-orange-500 transition-colors hover:border-orange-500 hover:bg-orange-500 hover:text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
                >
                  <Icon aria-hidden="true" className="size-5" />
                </a>
              ))}
            </div>
          </div>

          <nav aria-labelledby="footer-quick-links-heading">
            <h2 id="footer-quick-links-heading" className="text-lg font-semibold text-zinc-100">
              {t('footer.quickLinks')}
            </h2>
            <ul className="mt-4 space-y-3">
              {quickLinks.map((link) => (
                <li key={link.href}>
                  <a
                    href={link.href}
                    className="rounded-sm text-base text-zinc-400 transition-colors hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                  >
                    {t(link.translationKey)}
                  </a>
                </li>
              ))}
            </ul>
          </nav>

          <div>
            <h2 className="text-lg font-semibold text-zinc-100">{t('footer.support')}</h2>
            <a
              href="https://vgu.edu.vn/international-office"
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex items-center gap-2 rounded-sm text-base text-zinc-400 transition-colors hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
            >
              {t('footer.helpCenter')}
              <ExternalLink aria-hidden="true" className="size-4" />
            </a>
          </div>
        </div>

        <div className="mt-12 border-t border-white/10 pt-8 text-center">
          <p className="text-sm leading-6 text-zinc-500">
            {t('footer.copyright', { year: currentYear })}
          </p>
        </div>
      </div>
    </footer>
  )
}

export { Footer }
