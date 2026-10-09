import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  DISPLAY_DURATION_MS,
  HeroBackgroundSlideshow,
  TRANSITION_DURATION_MS,
} from '@/components/landing/hero-background-slideshow'

let reducedMotion = false
let documentHidden = false
let decodeImage: ReturnType<typeof vi.fn>

const originalDecodeDescriptor = Object.getOwnPropertyDescriptor(
  HTMLImageElement.prototype,
  'decode',
)
const originalHiddenDescriptor = Object.getOwnPropertyDescriptor(document, 'hidden')

function mockReducedMotion(matches: boolean) {
  reducedMotion = matches
  Object.defineProperty(window, 'matchMedia', {
    configurable: true,
    writable: true,
    value: vi.fn().mockImplementation(() => ({
      get matches() {
        return reducedMotion
      },
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

async function advancePhase(durationMs: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(durationMs)
  })
}

function visibleLayer() {
  return [
    screen.getByTestId('hero-background-layer-0'),
    screen.getByTestId('hero-background-layer-1'),
  ].find((image) => image.classList.contains('opacity-100'))
}

function finishOpacityTransition() {
  const outgoingLayer = [
    screen.getByTestId('hero-background-layer-0'),
    screen.getByTestId('hero-background-layer-1'),
  ].find((image) => image.classList.contains('opacity-0'))

  fireEvent.transitionEnd(outgoingLayer!, { propertyName: 'opacity' })
}

describe('HeroBackgroundSlideshow', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    mockReducedMotion(false)
    documentHidden = false
    Object.defineProperty(document, 'hidden', {
      configurable: true,
      get: () => documentHidden,
    })
    decodeImage = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(HTMLImageElement.prototype, 'decode', {
      configurable: true,
      writable: true,
      value: decodeImage,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
    if (originalDecodeDescriptor)
      Object.defineProperty(HTMLImageElement.prototype, 'decode', originalDecodeDescriptor)
    else delete (HTMLImageElement.prototype as { decode?: unknown }).decode
    if (originalHiddenDescriptor)
      Object.defineProperty(document, 'hidden', originalHiddenDescriptor)
  })

  it('keeps two stable layers and changes only the fully transparent source after a crossfade', async () => {
    render(<HeroBackgroundSlideshow />)

    const slideshow = screen.getByTestId('hero-background-slideshow')
    const layer0 = screen.getByTestId('hero-background-layer-0')
    const layer1 = screen.getByTestId('hero-background-layer-1')
    const firstSource = layer0.getAttribute('src')
    const secondSource = layer1.getAttribute('src')

    expect(slideshow).toHaveAttribute('data-phase', 'display')
    expect(layer0).toHaveAttribute('data-slide-index', '0')
    expect(layer1).toHaveAttribute('data-slide-index', '1')
    expect(layer0).toHaveClass('opacity-100')
    expect(layer1).toHaveClass('opacity-0')
    expect(vi.getTimerCount()).toBe(1)

    await advancePhase(DISPLAY_DURATION_MS)
    expect(slideshow).toHaveAttribute('data-phase', 'transition')
    expect(layer0).toHaveClass('opacity-0')
    expect(layer1).toHaveClass('opacity-100')
    expect(layer0).toHaveAttribute('src', firstSource)
    expect(layer1).toHaveAttribute('src', secondSource)
    expect(vi.getTimerCount()).toBe(0)

    await advancePhase(TRANSITION_DURATION_MS)
    finishOpacityTransition()
    expect(slideshow).toHaveAttribute('data-phase', 'display')
    expect(layer0).toHaveClass('opacity-0')
    expect(layer1).toHaveClass('opacity-100')
    expect(layer0).toHaveAttribute('data-slide-index', '2')
    expect(layer1).toHaveAttribute('data-slide-index', '1')
    expect(layer1).toHaveAttribute('src', secondSource)
  })

  it('waits for the incoming image to decode before starting the transition', async () => {
    let finishDecode: (() => void) | undefined
    decodeImage.mockReturnValueOnce(
      new Promise<void>((resolve) => {
        finishDecode = resolve
      }),
    )
    render(<HeroBackgroundSlideshow />)

    await advancePhase(DISPLAY_DURATION_MS)
    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute('data-phase', 'display')
    expect(visibleLayer()).toHaveAttribute('data-slide-index', '0')

    await act(async () => finishDecode?.())
    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute(
      'data-phase',
      'transition',
    )
    expect(visibleLayer()).toHaveAttribute('data-slide-index', '1')
  })

  it('pauses the display timer while the document is hidden', async () => {
    render(<HeroBackgroundSlideshow />)

    await advancePhase(3_000)
    act(() => {
      documentHidden = true
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await advancePhase(DISPLAY_DURATION_MS * 2)
    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute('data-phase', 'display')
    expect(visibleLayer()).toHaveAttribute('data-slide-index', '0')

    act(() => {
      documentHidden = false
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await advancePhase(3_999)
    expect(visibleLayer()).toHaveAttribute('data-slide-index', '0')
    await advancePhase(1)
    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute(
      'data-phase',
      'transition',
    )

    await advancePhase(400)
    act(() => {
      documentHidden = true
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await advancePhase(TRANSITION_DURATION_MS * 2)
    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute(
      'data-phase',
      'transition',
    )

    act(() => {
      documentHidden = false
      document.dispatchEvent(new Event('visibilitychange'))
    })
    await advancePhase(599)
    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute(
      'data-phase',
      'transition',
    )
    await advancePhase(1)
    finishOpacityTransition()
    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute('data-phase', 'display')
    expect(visibleLayer()).toHaveAttribute('data-slide-index', '1')
  })

  it('runs three complete loops including the fifth-to-first transition with at most one timer', async () => {
    const { unmount } = render(<HeroBackgroundSlideshow />)

    for (let transition = 1; transition <= 15; transition += 1) {
      await advancePhase(DISPLAY_DURATION_MS)
      expect(vi.getTimerCount()).toBe(0)
      await advancePhase(TRANSITION_DURATION_MS)
      finishOpacityTransition()
      expect(visibleLayer()).toHaveAttribute('data-slide-index', String(transition % 5))
      expect(vi.getTimerCount()).toBe(1)
    }

    expect(decodeImage).toHaveBeenCalledTimes(16)
    unmount()
    expect(vi.getTimerCount()).toBe(0)
  })

  it('uses one static background without timers when reduced motion is requested', () => {
    mockReducedMotion(true)
    render(<HeroBackgroundSlideshow />)

    expect(screen.getByTestId('hero-background-slideshow')).toHaveAttribute(
      'data-phase',
      'reduced-motion',
    )
    expect(screen.getByTestId('hero-background-static')).toHaveAttribute('data-slide-index', '0')
    expect(screen.queryByTestId('hero-background-layer-0')).not.toBeInTheDocument()
    expect(vi.getTimerCount()).toBe(0)
  })
})
