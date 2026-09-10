import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TestimonialsMarquee } from '@/components/landing/testimonials-marquee'
import i18n from '@/i18n'

interface AnimationFrameController {
  runFrame: (timestamp: number) => void
}

function mockAnimationFrames(): AnimationFrameController {
  let nextId = 1
  let callbacks = new Map<number, FrameRequestCallback>()

  vi.spyOn(window, 'requestAnimationFrame').mockImplementation((callback) => {
    const id = nextId
    nextId += 1
    callbacks.set(id, callback)
    return id
  })
  vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id) => {
    callbacks.delete(id)
  })

  return {
    runFrame(timestamp) {
      const currentCallbacks = callbacks
      callbacks = new Map()
      act(() => {
        for (const callback of currentCallbacks.values()) callback(timestamp)
      })
    },
  }
}

function mockReducedMotion(initialMatches: boolean) {
  let matches = initialMatches
  const listeners = new Set<() => void>()
  const mediaQuery = {
    get matches() {
      return matches
    },
    media: '(prefers-reduced-motion: reduce)',
    onchange: null,
    addEventListener: (_event: string, listener: () => void) => {
      listeners.add(listener)
    },
    removeEventListener: (_event: string, listener: () => void) => {
      listeners.delete(listener)
    },
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  }

  vi.spyOn(window, 'matchMedia').mockReturnValue(mediaQuery as unknown as MediaQueryList)

  return {
    setMatches(nextMatches: boolean) {
      matches = nextMatches
      act(() => {
        for (const listener of listeners) listener()
      })
    },
  }
}

describe('TestimonialsMarquee', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  afterEach(() => {
    vi.restoreAllMocks()
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

  it('moves by elapsed time and loops both rows at the duplicated-content boundary', () => {
    vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get').mockReturnValue(120)
    const frames = mockAnimationFrames()
    const { container } = render(<TestimonialsMarquee />)
    const leftTrack = container.querySelector<HTMLElement>('[data-marquee-track="left"]')!
    const rightTrack = container.querySelector<HTMLElement>('[data-marquee-track="right"]')!

    expect(rightTrack).toHaveStyle({ transform: 'translateX(-60px)' })

    frames.runFrame(0)
    frames.runFrame(500)
    expect(leftTrack).toHaveStyle({ transform: 'translateX(-15px)' })
    expect(rightTrack).toHaveStyle({ transform: 'translateX(-45px)' })

    frames.runFrame(2_000)
    expect(leftTrack).toHaveStyle({ transform: 'translateX(0px)' })
    expect(rightTrack).toHaveStyle({ transform: 'translateX(-60px)' })
  })

  it('pauses on pointer hover and resumes without a position jump', () => {
    vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get').mockReturnValue(1_200)
    const frames = mockAnimationFrames()
    const { container } = render(<TestimonialsMarquee />)
    const leftRow = container.querySelector<HTMLElement>('[data-marquee-row="left"]')!
    const leftTrack = container.querySelector<HTMLElement>('[data-marquee-track="left"]')!

    frames.runFrame(0)
    frames.runFrame(500)
    expect(leftTrack).toHaveStyle({ transform: 'translateX(-15px)' })

    fireEvent.pointerEnter(leftRow)
    frames.runFrame(1_500)
    expect(leftTrack).toHaveStyle({ transform: 'translateX(-15px)' })

    fireEvent.pointerLeave(leftRow)
    frames.runFrame(2_000)
    expect(leftTrack).toHaveStyle({ transform: 'translateX(-30px)' })
  })

  it('does not animate when reduced motion is already enabled', () => {
    mockReducedMotion(true)
    const requestAnimationFrame = vi.spyOn(window, 'requestAnimationFrame')

    render(<TestimonialsMarquee />)

    expect(requestAnimationFrame).not.toHaveBeenCalled()
  })

  it('stops scheduled animation when reduced motion becomes enabled', () => {
    const reducedMotion = mockReducedMotion(false)
    mockAnimationFrames()
    const cancelAnimationFrame = vi.spyOn(window, 'cancelAnimationFrame')

    render(<TestimonialsMarquee />)
    reducedMotion.setMatches(true)

    expect(cancelAnimationFrame).toHaveBeenCalledTimes(2)
  })

  it('cancels both animation frames when unmounted', () => {
    mockAnimationFrames()
    const cancelAnimationFrame = vi.spyOn(window, 'cancelAnimationFrame')
    const { unmount } = render(<TestimonialsMarquee />)

    unmount()

    expect(cancelAnimationFrame).toHaveBeenCalledTimes(2)
  })
})
