import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'

import { TestimonialsMarquee } from '@/components/landing/testimonials-marquee'
import i18n from '@/i18n'

describe('TestimonialsMarquee', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders section title and subtitle', () => {
    render(<TestimonialsMarquee />)

    expect(screen.getByRole('heading', { name: 'What Students Say' })).toBeVisible()
    expect(
      screen.getByText(
        'Hear from real VGU students about their experiences with the Buddy Program.',
      ),
    ).toBeVisible()
  })

  it('renders all 12 testimonials (each appears twice for seamless loop)', () => {
    render(<TestimonialsMarquee />)

    // Each testimonial appears once in the original set and once in the clone.
    // We check that the first and last testimonial text is present.
    const first = screen.getAllByText(
      (_, el) => el?.textContent?.includes('VGU Buddy transformed my university experience') ?? false,
    )
    // Original + clone = at least 2
    expect(first.length).toBeGreaterThanOrEqual(2)

    const last = screen.getAllByText(
      (_, el) => el?.textContent?.includes('young, enthusiastic, and energetic club') ?? false,
    )
    expect(last.length).toBeGreaterThanOrEqual(2)
  })

  it('keeps visual clones out of the accessibility tree', () => {
    const { container } = render(<TestimonialsMarquee />)
    const quotes = container.querySelectorAll('blockquote')
    const visualClones = container.querySelectorAll('[data-marquee-clone="true"]')

    // The seamless loop still needs 24 visual cards in the DOM.
    expect(quotes).toHaveLength(24)
    expect(visualClones).toHaveLength(12)

    for (const clone of visualClones) {
      expect(clone).toHaveAttribute('aria-hidden', 'true')
    }

    // Assistive technology must encounter each unique testimonial only once.
    expect(screen.getAllByRole('blockquote')).toHaveLength(12)
  })

  it('uses German content after a language change', async () => {
    await i18n.changeLanguage('de')
    render(<TestimonialsMarquee />)

    expect(screen.getByRole('heading', { name: 'Was Studierende sagen' })).toBeVisible()

    const germanQuote = screen.getAllByText(
      (_, el) =>
        el?.textContent?.includes('VGU Buddy hat mein Unileben verändert') ?? false,
    )
    expect(germanQuote.length).toBeGreaterThanOrEqual(2)
  })

  it('does not contain links or navigation elements', () => {
    const { container } = render(<TestimonialsMarquee />)
    const section = container.querySelector('#community')!

    expect(section.querySelectorAll('a')).toHaveLength(0)
    expect(section.querySelectorAll('button')).toHaveLength(0)
  })
})
