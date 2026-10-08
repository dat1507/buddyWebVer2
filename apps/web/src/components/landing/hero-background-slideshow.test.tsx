import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  DISPLAY_DURATION_MS,
  HeroBackgroundSlideshow,
  TRANSITION_DURATION_MS,
} from '@/components/landing/hero-background-slideshow'

function mockReducedMotion(matches: boolean) {
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      matches,
      media: '(prefers-reduced-motion: reduce)',
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  })
}

describe('HeroBackgroundSlideshow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockReducedMotion(false)
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('crossfades between a bounded current/next pair and advances continuously', () => {
    render(<HeroBackgroundSlideshow />)

    const current = screen.getByTestId('hero-background-current')
    const next = screen.getByTestId('hero-background-next')
    expect(current).toHaveAttribute('data-slide-index', '0')
    expect(next).toHaveAttribute('data-slide-index', '1')
    expect(current).toHaveClass('opacity-100')
    expect(next).toHaveClass('opacity-0')

    act(() => vi.advanceTimersByTime(DISPLAY_DURATION_MS))
    expect(current).toHaveClass('opacity-0')
    expect(next).toHaveClass('opacity-100')

    act(() => vi.advanceTimersByTime(TRANSITION_DURATION_MS))
    expect(screen.getByTestId('hero-background-current')).toHaveAttribute('data-slide-index', '1')
    expect(screen.getByTestId('hero-background-next')).toHaveAttribute('data-slide-index', '2')
  })

  it('uses one static background when reduced motion is requested', () => {
    mockReducedMotion(true)
    render(<HeroBackgroundSlideshow />)

    expect(screen.getByTestId('hero-background-current')).toHaveAttribute('data-slide-index', '0')
    expect(screen.queryByTestId('hero-background-next')).not.toBeInTheDocument()

    act(() => vi.advanceTimersByTime((DISPLAY_DURATION_MS + TRANSITION_DURATION_MS) * 2))
    expect(screen.getByTestId('hero-background-current')).toHaveAttribute('data-slide-index', '0')
  })
})
