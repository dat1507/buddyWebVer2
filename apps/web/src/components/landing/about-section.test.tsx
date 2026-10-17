import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { AboutSection } from '@/components/landing/about-section'
import i18n from '@/i18n'

describe('AboutSection', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })
  it('introduces the product, retains the real photo and adds no CTA', () => {
    const { container } = render(<AboutSection />)
    for (const name of ['Buddy Matching', 'Invitations & Chat', 'Events & Community']) {
      expect(screen.getByRole('heading', { name })).toBeVisible()
    }
    expect(screen.getByRole('img', { name: 'VGU Buddy Program members together' })).toBeVisible()
    expect(container.querySelector('#about')).toHaveClass('scroll-mt-20')
    expect(screen.queryByRole('link')).toBeNull()
  })
  it.each(['en', 'de'])('updates all steps and visuals in %s', async (language) => {
    await i18n.changeLanguage(language)
    render(<AboutSection />)
    const tabs = screen.getAllByRole('tab')
    const keys = ['profile', 'discover', 'connect']
    tabs.forEach((tab, index) => {
      fireEvent.click(tab)
      expect(tab).toHaveAttribute('aria-selected', 'true')
      expect(screen.getByRole('tabpanel')).toHaveAccessibleName(
        i18n.t(`howItWorks.${keys[index]}.title`),
      )
      expect(screen.getByText(i18n.t(`howItWorks.${keys[index]}.desc`))).toBeVisible()
      expect(screen.getByText(i18n.t('howItWorks.illustration'))).toBeVisible()
    })
    expect(screen.getByText(i18n.t('howItWorks.accepted'))).toBeVisible()
    expect(screen.getAllByRole('tab')).toHaveLength(3)
  })
  it('supports roving focus, arrow wrapping, Home and End', () => {
    render(<AboutSection />)
    const tabs = screen.getAllByRole('tab')
    tabs[0].focus()
    for (const [key, index] of [
      ['ArrowLeft', 2],
      ['ArrowRight', 0],
      ['End', 2],
      ['Home', 0],
      ['ArrowRight', 1],
    ] as const) {
      fireEvent.keyDown(document.activeElement!, { key })
      expect(tabs[index]).toHaveFocus()
      expect(tabs[index]).toHaveAttribute('tabindex', '0')
      expect(tabs[index]).toHaveAttribute('aria-selected', 'true')
      expect(tabs.filter((tab) => tab.tabIndex === 0)).toHaveLength(1)
    }
    expect(screen.getByText('87%')).toBeVisible()
    expect(screen.getByText('View Profile')).toBeVisible()
    expect(screen.getByText('Send Invitation')).toBeVisible()
  })
})
