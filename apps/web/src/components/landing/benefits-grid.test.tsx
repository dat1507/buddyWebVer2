import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { BenefitsGrid } from '@/components/landing/benefits-grid'
import i18n from '@/i18n'

describe('Campus Resources', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })
  it.each([
    [
      'en',
      'Explore VGU Campus Resources',
      ['Library', 'Sports Hall', 'International Office', 'Dormitory Service'],
    ],
    [
      'de',
      'Entdecke die Campus-Angebote der VGU',
      ['Bibliothek', 'Sporthalle', 'International Office', 'Wohnheimservice'],
    ],
  ] as const)(
    'renders exactly four %s campus resources in order',
    async (language, title, headings) => {
      await i18n.changeLanguage(language)
      render(<BenefitsGrid />)
      expect(screen.getByRole('region', { name: title })).toHaveAttribute('id', 'features')
      expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual(
        headings,
      )
      expect(screen.queryByText('Merchandise')).not.toBeInTheDocument()
      expect(screen.queryByText('Events Recap')).not.toBeInTheDocument()
    },
  )
  it('retains exact official destinations and accessible secure external navigation', () => {
    render(<BenefitsGrid />)
    const links = screen.getAllByRole('link')
    expect(links.map((link) => link.getAttribute('href'))).toEqual([
      'https://library.vgu.edu.vn/',
      'https://vgu.edu.vn/sports-complex',
      'https://vgu.edu.vn/international-office',
      'https://dorm.vgu.edu.vn/',
    ])
    for (const link of links) {
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
      expect(link).toHaveClass('min-h-11', 'focus-visible:ring-2')
      expect(link).toHaveAccessibleName(/opens in a new tab/)
    }
    links[0].focus()
    expect(links[0]).toHaveFocus()
  })
})
