import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { PublicLayout } from '@/components/layout/public-layout'
import { LandingPage } from '@/pages/public/landing-page'
import i18n from '@/i18n'

function renderLandingPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<PublicLayout />}>
            <Route index element={<LandingPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LandingPage (FE-019 Assembly)', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders all 6 landing sections in the correct sequence within <main>', () => {
    const { container } = renderLandingPage()
    const main = container.querySelector('main')
    expect(main).toBeInTheDocument()

    const sections = Array.from(main!.querySelectorAll('section'))
    expect(sections).toHaveLength(6)

    // Sections order: Hero, EventsSlider, About, Benefits, Testimonials, CTA
    expect(sections[0].id).toBe('home')
    expect(sections[1].getAttribute('aria-labelledby')).toBe('events-title')
    expect(sections[2].id).toBe('about')
    expect(sections[3].id).toBe('features')
    expect(sections[4].id).toBe('community')
    expect(sections[5].id).toBe('cta')
  })

  it('has exactly one <h1> heading on the page for SEO best practices', () => {
    renderLandingPage()
    const h1s = screen.getAllByRole('heading', { level: 1 })
    expect(h1s).toHaveLength(1)
    expect(h1s[0]).toHaveTextContent(/Connect with/i)
  })

  it('renders exactly one header, main, and footer through PublicLayout', () => {
    const { container } = renderLandingPage()

    expect(container.querySelectorAll('header')).toHaveLength(1)
    expect(container.querySelectorAll('main')).toHaveLength(1)
    expect(container.querySelectorAll('footer')).toHaveLength(1)
  })

  it('renders section headings for all assembled sections', () => {
    renderLandingPage()

    // Hero h1
    expect(screen.getByRole('heading', { level: 1, name: /Connect with/i })).toBeVisible()

    // EventsSlider h2
    expect(screen.getByRole('heading', { level: 2, name: 'Upcoming Events' })).toBeVisible()

    // AboutSection h2
    expect(screen.getByRole('heading', { level: 2, name: 'Why Choose VGU Buddy?' })).toBeVisible()

    // BenefitsGrid h2
    expect(screen.getByRole('heading', { level: 2, name: 'Outstanding Benefits' })).toBeVisible()

    // TestimonialsMarquee h2
    expect(screen.getByRole('heading', { level: 2, name: 'What Students Say' })).toBeVisible()

    // CtaSection h2
    expect(
      screen.getByRole('heading', {
        level: 2,
        name: 'Ready to Transform Your University Experience?',
      }),
    ).toBeVisible()
  })

  it('updates all section headings when switching language to German', async () => {
    await i18n.changeLanguage('de')
    renderLandingPage()

    expect(screen.getByRole('heading', { level: 1, name: /Verbinde dich mit/i })).toBeVisible()
    expect(
      screen.getByRole('heading', { level: 2, name: 'Bevorstehende Veranstaltungen' }),
    ).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: 'Warum VGU Buddy wählen?' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: 'Hervorragende Vorteile' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 2, name: 'Was Studierende sagen' })).toBeVisible()
    expect(
      screen.getByRole('heading', {
        level: 2,
        name: 'Bereit, dein Unileben zu transformieren?',
      }),
    ).toBeVisible()
  })

  it('contains valid section anchors matching navigation targets', () => {
    const { container } = renderLandingPage()

    const expectedAnchors = ['home', 'about', 'features', 'community', 'contact']
    for (const anchor of expectedAnchors) {
      const el = container.querySelector(`#${anchor}`)
      expect(el).not.toBeNull()
    }
  })
})
