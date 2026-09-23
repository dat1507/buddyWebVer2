import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AvatarCropDialog } from '@/features/profile/avatar-crop-dialog'
import i18n from '@/i18n'

const source = {
  file: new File([new Uint8Array([0xff, 0xd8, 0xff])], 'portrait.jpg', {
    type: 'image/jpeg',
  }),
  url: 'blob:portrait',
}

describe('AvatarCropDialog', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('supports keyboard repositioning and exports an optimized square WebP', async () => {
    const drawImage = vi.fn()
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      drawImage,
      imageSmoothingEnabled: false,
      imageSmoothingQuality: 'low',
    } as unknown as CanvasRenderingContext2D)
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback, type) => {
      callback(new Blob([new Uint8Array([1, 2, 3])], { type: type ?? 'image/png' }))
    })
    const onApply = vi.fn()

    render(<AvatarCropDialog open source={source} onCancel={vi.fn()} onApply={onApply} />)
    const image = document.querySelector('img[src="blob:portrait"]') as HTMLImageElement
    Object.defineProperties(image, {
      naturalWidth: { configurable: true, value: 4024 },
      naturalHeight: { configurable: true, value: 6048 },
    })
    fireEvent.load(image)

    const cropArea = screen.getByRole('img', { name: /Profile photo crop area/ })
    cropArea.focus()
    fireEvent.keyDown(cropArea, { key: 'ArrowDown' })
    fireEvent.change(screen.getByLabelText('Zoom'), { target: { value: '1.5' } })
    fireEvent.click(screen.getByRole('button', { name: 'Use this crop' }))

    await waitFor(() => expect(onApply).toHaveBeenCalledOnce())
    const output = onApply.mock.calls[0][0] as File
    expect(output).toMatchObject({ name: 'avatar.webp', type: 'image/webp' })
    expect(drawImage).toHaveBeenCalledOnce()
    expect(drawImage.mock.calls[0].slice(-4)).toEqual([0, 0, 800, 800])
  })

  it('rejects excessive decoded dimensions before enabling the crop action', () => {
    render(<AvatarCropDialog open source={source} onCancel={vi.fn()} onApply={vi.fn()} />)
    const image = document.querySelector('img[src="blob:portrait"]') as HTMLImageElement
    Object.defineProperties(image, {
      naturalWidth: { configurable: true, value: 9000 },
      naturalHeight: { configurable: true, value: 9000 },
    })
    fireEvent.load(image)

    expect(screen.getByRole('alert')).toHaveTextContent('8192 px')
    expect(screen.getByRole('button', { name: 'Use this crop' })).toBeDisabled()
  })

  it('closes with Escape and restores focus to the previous control', () => {
    const trigger = document.createElement('button')
    document.body.append(trigger)
    trigger.focus()
    const onCancel = vi.fn()
    const view = render(
      <AvatarCropDialog open source={source} onCancel={onCancel} onApply={vi.fn()} />,
    )

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onCancel).toHaveBeenCalledOnce()
    view.unmount()
    expect(trigger).toHaveFocus()
    trigger.remove()
  })
})
