import { render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { Footer } from '@/components/layout/footer'
import i18n from '@/i18n'

describe('Minimal Branding Footer', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })
  afterEach(() => {
    vi.useRealTimers()
  })

  it('replaces duplicated navigation and Support with Get in Touch', () => {
    render(<Footer />)
    const footer = screen.getByRole('contentinfo')
    expect(footer).toHaveAttribute('id', 'contact')
    expect(within(footer).queryByRole('navigation')).not.toBeInTheDocument()
    expect(within(footer).queryByText('Quick Links')).not.toBeInTheDocument()
    expect(within(footer).queryByText('Support')).not.toBeInTheDocument()
    expect(
      within(footer).queryByRole('link', { name: 'International Office' }),
    ).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Get in Touch' })).toBeVisible()
    expect(
      screen.getByText(
        'Connecting students and building a stronger community at Vietnamese-German University.',
      ),
    ).toBeVisible()
    expect(
      screen.getByText("Have questions or suggestions? We'd love to hear from you."),
    ).toBeVisible()
    const contact = screen.getByRole('link', { name: 'Contact Us' })
    expect(contact).toHaveAttribute('href', 'mailto:vgubuddy@vgu.edu.vn')
    expect(contact).toHaveClass('min-h-11', 'focus-visible:ring-2')
    contact.focus()
    expect(contact).toHaveFocus()
    expect(screen.getByText('vgubuddy@vgu.edu.vn')).toBeVisible()
    expect(footer.querySelector('form, button')).toBeNull()
    expect(within(footer).getAllByRole('link')).toHaveLength(4)
  })

  it('preserves the logo and exact secure social destinations', () => {
    render(<Footer />)
    const brand = screen.getByRole('link', { name: 'VGU Buddy Program' })
    expect(brand).toHaveAttribute('href', '/#home')
    expect(brand.querySelector('img')).toHaveClass('h-12', 'w-12')
    for (const [name, href] of [
      ['Facebook', 'https://www.facebook.com/VGUBuddyProgram'],
      ['Instagram', 'https://www.instagram.com/buddyprogram_vgu/'],
    ]) {
      const link = screen.getByRole('link', { name })
      expect(link).toHaveAttribute('href', href)
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
      expect(link).toHaveClass('size-11', 'focus-visible:ring-2', 'motion-reduce:transition-none')
    }
  })

  it('localizes all contact copy in German while preserving the email', async () => {
    await i18n.changeLanguage('de')
    render(<Footer />)
    expect(screen.getByRole('heading', { name: 'Kontakt aufnehmen' })).toBeVisible()
    expect(
      screen.getByText(
        'Wir verbinden Studierende und stärken die Gemeinschaft an der Vietnamesisch-Deutschen Universität.',
      ),
    ).toBeVisible()
    expect(
      screen.getByText('Hast du Fragen oder Anregungen? Wir freuen uns auf deine Nachricht.'),
    ).toBeVisible()
    expect(screen.getByRole('link', { name: 'Kontaktiere uns' })).toHaveAttribute(
      'href',
      'mailto:vgubuddy@vgu.edu.vn',
    )
    expect(screen.getByText(/Verfügbar auf Englisch & Deutsch/)).toBeVisible()
  })

  it('retains the dynamic copyright year and language availability', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2031-06-15T12:00:00Z'))
    render(<Footer />)
    expect(
      screen.getByText(
        '© 2031 VGU Buddy Program. All rights reserved. | Available in English & German',
      ),
    ).toBeVisible()
  })
})
