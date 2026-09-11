import { useEffect, useRef, useState } from 'react'
import { ChevronDown, ExternalLink, Menu, UserPlus, UserRound, X } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import vguBuddyLogo from '@/assets/vgu-buddy-logo.png'
import { LanguageToggle } from '@/components/layout/language-toggle'
import { Button } from '@/components/ui/button'
import { useModalIsolation } from '@/hooks/use-modal-isolation'

const navItems = [
  { href: '/#home', translationKey: 'nav.home' },
  { href: '/#about', translationKey: 'nav.about' },
  { href: '/#features', translationKey: 'nav.features' },
  { href: '/#community', translationKey: 'nav.community' },
  { href: '/#contact', translationKey: 'nav.contact' },
] as const

const survivalBookPath = '/documents/vgu-buddy-survival-book.pdf'

function Navbar() {
  const { t } = useTranslation()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isSignInMenuOpen, setIsSignInMenuOpen] = useState(false)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const drawerRef = useRef<HTMLElement>(null)
  const drawerOverlayRef = useRef<HTMLDivElement>(null)
  const signInButtonRef = useRef<HTMLButtonElement>(null)
  const signInMenuRef = useRef<HTMLElement>(null)

  useModalIsolation(drawerOverlayRef, isMenuOpen)

  useEffect(() => {
    if (!isMenuOpen) return

    const previousOverflow = document.body.style.overflow
    const menuButton = menuButtonRef.current
    document.body.style.overflow = 'hidden'
    closeButtonRef.current?.focus()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMenuOpen(false)
        return
      }

      if (event.key !== 'Tab' || !drawerRef.current) return

      const focusableElements = Array.from(
        drawerRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      )

      if (focusableElements.length === 0) return

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault()
        lastElement.focus()
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault()
        firstElement.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      document.removeEventListener('keydown', handleKeyDown)
      menuButton?.focus()
    }
  }, [isMenuOpen])

  useEffect(() => {
    if (!isSignInMenuOpen) return

    const handleMouseDown = (event: MouseEvent) => {
      const target = event.target
      if (!(target instanceof Node)) return
      if (signInButtonRef.current?.contains(target) || signInMenuRef.current?.contains(target)) {
        return
      }
      setIsSignInMenuOpen(false)
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setIsSignInMenuOpen(false)
      signInButtonRef.current?.focus()
    }

    document.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isSignInMenuOpen])

  const closeMenu = () => setIsMenuOpen(false)

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-black/90 backdrop-blur-lg">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <a
          href="/#home"
          className="flex min-w-0 items-center gap-2 rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
          aria-label="VGU Buddy Program"
        >
          <img src={vguBuddyLogo} alt="" className="h-11 w-11 shrink-0 rounded-full object-cover" />
          <span className="truncate text-base font-semibold tracking-wide text-white sm:text-lg">
            VGU Buddy
          </span>
        </a>

        <nav className="hidden items-center gap-1 lg:flex" aria-label={t('nav.primaryNavigation')}>
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded-md px-3 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
            >
              {t(item.translationKey)}
            </a>
          ))}
          <a
            href={survivalBookPath}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium text-zinc-300 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
          >
            {t('nav.surbook')}
            <ExternalLink aria-hidden="true" className="size-3.5" />
          </a>
        </nav>

        <div className="flex items-center gap-2">
          <div className="hidden sm:inline-flex">
            <LanguageToggle />
          </div>

          <div className="relative hidden lg:block">
            <Button
              ref={signInButtonRef}
              type="button"
              variant="outline"
              className="gap-2 border-white/15 bg-white/[0.04] text-zinc-100 hover:border-orange-500/50 hover:bg-orange-500/10 hover:text-orange-300"
              aria-haspopup="true"
              aria-expanded={isSignInMenuOpen}
              aria-controls="desktop-sign-in-menu"
              onClick={() => setIsSignInMenuOpen((isOpen) => !isOpen)}
            >
              <UserRound aria-hidden="true" className="size-4" />
              {t('nav.signIn')}
              <ChevronDown
                aria-hidden="true"
                className={`size-4 transition-transform ${isSignInMenuOpen ? 'rotate-180' : ''}`}
              />
            </Button>

            {isSignInMenuOpen ? (
              <nav
                ref={signInMenuRef}
                id="desktop-sign-in-menu"
                aria-label={t('nav.accountNavigation')}
                className="absolute right-0 top-[calc(100%+0.5rem)] z-50 w-64 rounded-xl border border-white/10 bg-zinc-950 p-2 shadow-2xl shadow-black/50"
              >
                <Link
                  to="/login"
                  className="block rounded-lg px-3 py-2.5 text-sm font-medium text-zinc-200 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                  onClick={() => setIsSignInMenuOpen(false)}
                >
                  {t('nav.userLogin')}
                </Link>
                <Link
                  to="/register"
                  className="mt-1 block rounded-lg px-3 py-2.5 text-sm font-medium text-zinc-200 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                  onClick={() => setIsSignInMenuOpen(false)}
                >
                  {t('nav.createStudentAccount')}
                </Link>
              </nav>
            ) : null}
          </div>

          <Button
            ref={menuButtonRef}
            type="button"
            variant="ghost"
            size="icon"
            className="text-zinc-100 hover:bg-white/10 hover:text-orange-400 lg:hidden"
            aria-label={t('nav.openMenu')}
            aria-expanded={isMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setIsMenuOpen(true)}
          >
            <Menu aria-hidden="true" className="size-5" />
          </Button>
        </div>
      </div>

      {isMenuOpen ? (
        <div ref={drawerOverlayRef} className="fixed inset-0 top-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 h-full w-full cursor-default bg-black/70 backdrop-blur-sm"
            aria-label={t('nav.closeMenu')}
            onClick={closeMenu}
          />

          <aside
            ref={drawerRef}
            id="mobile-navigation"
            role="dialog"
            aria-modal="true"
            aria-label={t('nav.primaryNavigation')}
            className="absolute right-0 top-0 flex h-dvh w-[min(22rem,88vw)] flex-col border-l border-white/10 bg-zinc-950 p-5 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <span className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
                {t('nav.menu')}
              </span>
              <Button
                ref={closeButtonRef}
                type="button"
                variant="ghost"
                size="icon"
                className="text-zinc-100 hover:bg-white/10 hover:text-orange-400"
                aria-label={t('nav.closeMenu')}
                onClick={closeMenu}
              >
                <X aria-hidden="true" className="size-5" />
              </Button>
            </div>

            <nav
              className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto py-5"
              aria-label={t('nav.primaryNavigation')}
            >
              {navItems.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className="rounded-lg px-4 py-3 text-base font-medium text-zinc-200 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                  onClick={closeMenu}
                >
                  {t(item.translationKey)}
                </a>
              ))}
              <a
                href={survivalBookPath}
                target="_blank"
                rel="noreferrer"
                className="flex items-center justify-between rounded-lg px-4 py-3 text-base font-medium text-zinc-200 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                onClick={closeMenu}
              >
                {t('nav.surbook')}
                <ExternalLink aria-hidden="true" className="size-4" />
              </a>

              <div className="mt-4 space-y-1 border-t border-white/10 pt-4">
                <Link
                  to="/login"
                  className="flex items-center gap-3 rounded-lg px-4 py-3 text-base font-medium text-zinc-200 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                  onClick={closeMenu}
                >
                  <UserRound aria-hidden="true" className="size-4" />
                  {t('nav.userLogin')}
                </Link>
                <Link
                  to="/register"
                  className="flex items-center gap-3 rounded-lg px-4 py-3 text-base font-medium text-zinc-200 transition-colors hover:bg-white/5 hover:text-orange-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-500"
                  onClick={closeMenu}
                >
                  <UserPlus aria-hidden="true" className="size-4" />
                  {t('nav.createStudentAccount')}
                </Link>
              </div>
            </nav>

            <div className="border-t border-white/10 pt-4">
              <LanguageToggle variant="mobile" onToggle={closeMenu} />
            </div>
          </aside>
        </div>
      ) : null}
    </header>
  )
}

export { Navbar }
