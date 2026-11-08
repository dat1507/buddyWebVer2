import { useState } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { EventsSlider } from '@/components/landing/events-slider'
import { HeroSection } from '@/components/landing/hero-section'
import { LandingMotionContext } from '@/components/landing/landing-motion'
import { getStaticUpcomingEvents } from '@/features/events/data/static-upcoming-events'
import { ThemeContext, type ThemeId } from '@/features/site-theme/site-theme'
import i18n from '@/i18n'

vi.mock('@/components/landing/hero-background-slideshow', () => ({
  HeroBackgroundSlideshow: () => null,
}))

function Review({ theme = 'default' }: { theme?: ThemeId }) {
  const [paused, setPaused] = useState(false)
  return (
    <MemoryRouter>
      <LandingMotionContext value={{ paused, toggle: () => setPaused((value) => !value) }}>
        <ThemeContext.Provider value={theme}>
          <HeroSection />
        </ThemeContext.Provider>
        <EventsSlider events={getStaticUpcomingEvents('en')} />
      </LandingMotionContext>
    </MemoryRouter>
  )
}

describe('Landing motion control', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })
  afterEach(() => vi.useRealTimers())

  it('stops autoplay, preserves manual navigation and resumes the existing timer', async () => {
    vi.useFakeTimers()
    const { container } = render(<Review />)
    expect(container.querySelector('.season-scene')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Pause page animations' }))
    expect(screen.getByRole('button', { name: 'Resume page animations' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
    await act(() => vi.advanceTimersByTimeAsync(4000))
    const track = screen.getByTestId('event-slider-track')
    expect(track).toHaveAttribute('data-slide-index', '0')
    fireEvent.click(screen.getByRole('button', { name: 'Show next event' }))
    expect(track).toHaveAttribute('data-slide-index', '1')
    fireEvent.transitionEnd(track, { propertyName: 'transform' })
    fireEvent.click(screen.getByRole('button', { name: 'Resume page animations' }))
    await act(() => vi.advanceTimersByTimeAsync(3100))
    expect(track).toHaveAttribute('data-slide-index', '2')
  })

  it.each(['halloween', 'christmas', 'summer'] as const)(
    'keeps the %s illustration decorative and connected to the existing pause control',
    (theme) => {
      const { container } = render(<Review theme={theme} />)
      const scene = container.querySelector('svg[data-seasonal-scene]')
      expect(scene).toHaveAttribute('data-seasonal-scene', theme)
      expect(scene).toHaveAttribute('aria-hidden', 'true')
      expect(scene).toHaveAttribute('focusable', 'false')
      expect(scene).not.toHaveAttribute('data-motion-paused')
      fireEvent.click(screen.getByRole('button', { name: 'Pause page animations' }))
      expect(scene).toHaveAttribute('data-motion-paused', 'true')
      fireEvent.click(screen.getByRole('button', { name: 'Resume page animations' }))
      expect(scene).not.toHaveAttribute('data-motion-paused')
    },
  )

  it('localizes the control and announces its pressed state in German', async () => {
    await i18n.changeLanguage('de')
    render(<Review />)
    const control = screen.getByRole('button', { name: 'Seitenanimationen pausieren' })
    expect(control).toHaveAttribute('aria-pressed', 'false')
    fireEvent.click(control)
    expect(screen.getByRole('button', { name: 'Seitenanimationen fortsetzen' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })
})
