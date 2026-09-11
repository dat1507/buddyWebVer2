import { useState } from 'react'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { DemoVideoDialog } from '@/components/landing/demo-video-dialog'
import i18n from '@/i18n'

function DialogHarness() {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Open demo
      </button>
      <DemoVideoDialog open={open} onOpenChange={setOpen} />
    </>
  )
}

describe('DemoVideoDialog', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
  })

  afterEach(() => {
    cleanup()
    vi.restoreAllMocks()
    document.body.style.overflow = ''
  })

  it('mounts media only after opening and uses the approved playback attributes', () => {
    render(<DialogHarness />)

    const trigger = screen.getByRole('button', { name: 'Open demo' })
    const appContainer = trigger.parentElement
    expect(document.querySelector('video')).not.toBeInTheDocument()
    fireEvent.click(trigger)

    const dialog = screen.getByRole('dialog', { name: 'VGU Buddy Program Demo' })
    const video = screen.getByLabelText('VGU Buddy Program demo video')

    expect(dialog).toBeVisible()
    expect(video).toHaveAttribute('src', '/media/vgu-buddy-demo.mp4')
    expect(video).toHaveAttribute('poster', '/media/vgu-buddy-demo-poster.webp')
    expect(video).toHaveAttribute('controls')
    expect(video).toHaveAttribute('playsinline')
    expect(video).toHaveAttribute('preload', 'metadata')
    expect(video).not.toHaveAttribute('autoplay')
    expect(document.body).toHaveStyle({ overflow: 'hidden' })
    expect(screen.getByRole('button', { name: 'Close demo video' })).toHaveFocus()
    expect(appContainer).toHaveAttribute('aria-hidden', 'true')
    expect(appContainer).toHaveAttribute('inert')
  })

  it('closes on Escape, resets playback, unlocks scrolling, and returns focus', () => {
    const pause = vi.spyOn(HTMLMediaElement.prototype, 'pause')
    render(<DialogHarness />)
    const trigger = screen.getByRole('button', { name: 'Open demo' })

    trigger.focus()
    fireEvent.click(trigger)
    const video = screen.getByLabelText<HTMLVideoElement>('VGU Buddy Program demo video')
    video.currentTime = 12
    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(pause).toHaveBeenCalled()
    expect(video.currentTime).toBe(0)
    expect(document.body).not.toHaveStyle({ overflow: 'hidden' })
    expect(trigger).toHaveFocus()
    expect(trigger.parentElement).not.toHaveAttribute('aria-hidden')
    expect(trigger.parentElement).not.toHaveAttribute('inert')
  })

  it('closes only when the backdrop itself is clicked', () => {
    render(<DialogHarness />)
    fireEvent.click(screen.getByRole('button', { name: 'Open demo' }))

    fireEvent.click(screen.getByRole('dialog'))
    expect(screen.getByRole('dialog')).toBeVisible()

    fireEvent.click(screen.getByTestId('demo-video-backdrop'))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('closes from its localized close button', () => {
    render(<DialogHarness />)
    fireEvent.click(screen.getByRole('button', { name: 'Open demo' }))

    fireEvent.click(screen.getByRole('button', { name: 'Close demo video' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('contains keyboard focus within the dialog', () => {
    render(<DialogHarness />)
    fireEvent.click(screen.getByRole('button', { name: 'Open demo' }))
    const closeButton = screen.getByRole('button', { name: 'Close demo video' })
    const video = screen.getByLabelText('VGU Buddy Program demo video')

    expect(closeButton).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Tab', shiftKey: true })
    expect(video).toHaveFocus()
    fireEvent.keyDown(document, { key: 'Tab' })
    expect(closeButton).toHaveFocus()
  })

  it('reports loading and playback failure states accessibly', () => {
    render(<DialogHarness />)
    fireEvent.click(screen.getByRole('button', { name: 'Open demo' }))
    const video = screen.getByLabelText('VGU Buddy Program demo video')

    expect(screen.getByRole('status')).toHaveTextContent('Loading demo video')
    fireEvent.canPlay(video)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()

    fireEvent.loadStart(video)
    fireEvent.error(video)
    expect(screen.getByRole('alert')).toHaveTextContent(
      'The demo video could not be loaded. Please try again later.',
    )
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('localizes its accessible content in German', async () => {
    await i18n.changeLanguage('de')
    render(<DialogHarness />)
    fireEvent.click(screen.getByRole('button', { name: 'Open demo' }))

    expect(screen.getByRole('dialog', { name: 'VGU Buddy Program Demo' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Demo-Video schließen' })).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('Demo-Video wird geladen')
  })
})
