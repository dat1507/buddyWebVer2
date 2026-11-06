import type { SVGProps } from 'react'
import { ArrowUp, Mail } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import { useAuthStore } from '@/stores/auth-store'
import '@/styles/public-community.css'

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
  const status = useAuthStore((state) => state.status)
  const role = useAuthStore((state) => state.role)
  const currentYear = new Date().getFullYear()

  return (
    <footer id="contact" className="community-footer scroll-mt-24">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        <div className="footer-grid grid gap-10">
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
              {t('footer.tagline')}
              <span className="mt-3 block text-sm">{t('footer.description')}</span>
            </p>

            <div className="mt-6 flex gap-3">
              {socialLinks.map(({ href, label, Icon }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={label}
                  className="flex size-11 items-center justify-center rounded-lg border border-white/10 bg-black text-orange-500 transition-colors motion-reduce:transition-none hover:border-orange-500 hover:bg-orange-500 hover:text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
                >
                  <Icon aria-hidden="true" className="size-5" />
                </a>
              ))}
            </div>
          </div>

          <nav aria-labelledby="footer-explore-heading" className="footer-links">
            <h2 id="footer-explore-heading">{t('footer.explore')}</h2>
            {[
              ['home', 'home'],
              ['events', 'events'],
              ['about', 'about'],
              ['features', 'features'],
            ].map(([id, key]) => (
              <a key={id} href={`/#${id}`}>
                {t(`nav.${key}`)}
              </a>
            ))}
          </nav>
          <nav aria-labelledby="footer-community-heading" className="footer-links">
            <h2 id="footer-community-heading">{t('footer.community')}</h2>
            <a href="/#community">{t('nav.community')}</a>
            {status === 'authenticated' ? (
              <a href={role === 'ADMIN' ? '/admin/dashboard' : '/user/dashboard'}>
                {t('nav.openWorkspace')}
              </a>
            ) : (
              <a href="/login">{t('nav.userLogin')}</a>
            )}
            <h2 className="mt-6">{t('footer.information')}</h2>
            <a href="/documents/vgu-buddy-survival-book.pdf" target="_blank" rel="noreferrer">
              {t('nav.surbook')}
            </a>
          </nav>
          <div className="min-w-0" aria-labelledby="footer-contact-heading">
            <h2 id="footer-contact-heading" className="text-lg font-semibold text-zinc-100">
              {t('footer.getInTouch')}
            </h2>
            <p className="mt-4 max-w-md text-base leading-7 text-zinc-400">
              {t('footer.contactDescription')}
            </p>
            <a
              href="mailto:vgubuddy@vgu.edu.vn"
              className="mt-4 inline-flex min-h-11 items-center gap-2 rounded-md text-base font-medium text-orange-300 underline-offset-4 hover:text-orange-200 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950"
            >
              <Mail aria-hidden="true" className="size-5 shrink-0" />
              {t('footer.contactUs')}
            </a>
            <p className="mt-1 break-words text-sm leading-6 text-zinc-400">vgubuddy@vgu.edu.vn</p>
          </div>
        </div>

        <div className="footer-bottom mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-white/10 pt-8">
          <p className="text-sm leading-6 text-zinc-400">
            {t('footer.copyright', { year: currentYear })}
          </p>
          <a href="/#home" className="inline-flex min-h-11 items-center gap-2">
            {t('footer.backToTop')}
            <ArrowUp aria-hidden="true" className="size-4" />
          </a>
        </div>
      </div>
    </footer>
  )
}

export { Footer }
