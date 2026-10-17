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
      expect(screen.getAllByRole('img').map((image) => image.getAttribute('alt'))).toEqual(
        language === 'en'
          ? [
              'VGU library atrium with study spaces and central stairs',
              'Outdoor sports courts at the VGU campus',
              'International Office group beside the blue Einstein statue',
              'VGU student dormitory building and entrance walkway',
            ]
          : [
              'Atrium der VGU-Bibliothek mit Lernbereichen und zentraler Treppe',
              'Sportplätze auf dem VGU-Campus',
              'Gruppe des International Office neben der blauen Einstein-Statue',
              'VGU-Wohnheim mit Eingangsbereich und Fußweg',
            ],
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
  it('maps optimized local images to resources with reserved geometry and deferred loading', () => {
    render(<BenefitsGrid />)
    const images = screen.getAllByRole('img')
    const names = [
      'library.webp',
      'sports-hall.webp',
      'international-office.webp',
      'dormitory.webp',
    ]
    images.forEach((image, index) => {
      expect(image.getAttribute('src')).toContain('/campus-resources/' + names[index])
      expect(image).toHaveAttribute('loading', 'lazy')
      expect(image).toHaveAttribute('decoding', 'async')
      expect(Number(image.getAttribute('width'))).toBeGreaterThan(0)
      expect(Number(image.getAttribute('height'))).toBeGreaterThan(0)
      expect(image.parentElement).toHaveClass('aspect-video')
      expect(image).toHaveClass('object-cover')
    })
  })
})
