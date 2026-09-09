import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { AboutSection } from '@/components/landing/about-section'
import i18n from '@/i18n'

describe('AboutSection', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders all three feature cards and the group photo', () => {
    render(<AboutSection />)

    expect(screen.getByRole('heading', { name: 'Social Networking' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Events & Activities' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Campus Support' })).toBeVisible()
    expect(screen.getByRole('img', { name: 'VGU Buddy Program members together' })).toBeVisible()
  })

  it('uses German content after a language change', async () => {
    await i18n.changeLanguage('de')
    render(<AboutSection />)

    expect(screen.getByRole('heading', { name: 'Warum VGU Buddy wählen?' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Veranstaltungen & Aktivitäten' })).toBeVisible()
    expect(
      screen.getByRole('img', { name: 'Mitglieder des VGU Buddy Programms gemeinsam' }),
    ).toBeVisible()
  })
})
