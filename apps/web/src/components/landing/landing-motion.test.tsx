import { useState } from 'react'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { EventsSlider } from '@/components/landing/events-slider'
import { HeroSection } from '@/components/landing/hero-section'
import { LandingMotionContext } from '@/components/landing/landing-motion'
import { getStaticUpcomingEvents } from '@/features/events/data/static-upcoming-events'
import i18n from '@/i18n'

vi.mock('@/components/landing/hero-background-slideshow', () => ({
  HeroBackgroundSlideshow: () => null,
}))

function Review() {
  const [paused, setPaused] = useState(false)
  return (
    <MemoryRouter>
      <LandingMotionContext value={{ paused, toggle: () => setPaused((value) => !value) }}>
        <HeroSection />
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
    render(<Review />)
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
