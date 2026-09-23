import { describe, expect, it } from 'vitest'

import {
  MAX_AVATAR_SOURCE_BYTES,
  avatarCropLayout,
  avatarCropRect,
  clampAvatarOffset,
  validateAvatarSourceDimensions,
  validateAvatarSourceFile,
} from '@/features/profile/avatar-image'

const jpegHeader = new Uint8Array([0xff, 0xd8, 0xff, 0xe0])
const pngHeader = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])

describe('avatar image preparation', () => {
  it.each(['portrait.jpg', 'portrait.jpeg'])(
    'accepts a JPEG signature with the supported extension %s',
    async (name) => {
      const file = new File([jpegHeader], name, { type: 'image/jpeg' })
      await expect(validateAvatarSourceFile(file)).resolves.toBeNull()
    },
  )

  it('rejects mismatched MIME, extension, signature and oversized source data', async () => {
    await expect(
      validateAvatarSourceFile(new File([pngHeader], 'portrait.jpg', { type: 'image/png' })),
    ).resolves.toBe('unsupportedFormat')
    await expect(
      validateAvatarSourceFile(new File([pngHeader], 'portrait.jpg', { type: 'image/jpeg' })),
    ).resolves.toBe('signatureMismatch')

    const oversized = new File([jpegHeader], 'large.jpg', { type: 'image/jpeg' })
    Object.defineProperty(oversized, 'size', { value: MAX_AVATAR_SOURCE_BYTES + 1 })
    await expect(validateAvatarSourceFile(oversized)).resolves.toBe('sourceTooLarge')
  })

  it('allows the supplied 4024 × 6048 portrait while bounding decode memory', () => {
    expect(validateAvatarSourceDimensions(4024, 6048)).toBeNull()
    expect(validateAvatarSourceDimensions(8193, 100)).toBe('dimensionsTooLarge')
    expect(validateAvatarSourceDimensions(6000, 6000)).toBe('dimensionsTooLarge')
    expect(validateAvatarSourceDimensions(0, 100)).toBe('decodeError')
  })

  it('calculates a centered square crop and clamps image movement to covered bounds', () => {
    const layout = avatarCropLayout(4024, 6048, 320, 1)
    expect(layout.scale).toBeCloseTo(320 / 4024)
    expect(layout.maxOffsetX).toBeCloseTo(0)
    expect(layout.maxOffsetY).toBeGreaterThan(0)
    expect(clampAvatarOffset({ x: 100, y: 10_000 }, layout)).toEqual({
      x: 0,
      y: layout.maxOffsetY,
    })

    const crop = avatarCropRect(4024, 6048, 320, 1, { x: 0, y: 0 })
    expect(crop.sourceX).toBeCloseTo(0)
    expect(crop.sourceY).toBeCloseTo(1012)
    expect(crop.sourceSize).toBeCloseTo(4024)
  })
})
