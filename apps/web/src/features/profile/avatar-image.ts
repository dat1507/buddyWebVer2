const AVATAR_ACCEPT = 'image/jpeg,image/png,image/webp'
const MAX_AVATAR_SOURCE_BYTES = 12 * 1024 * 1024
const MAX_AVATAR_SOURCE_DIMENSION = 8192
const MAX_AVATAR_SOURCE_PIXELS = 32_000_000
const AVATAR_OUTPUT_SIZE = 800
const MAX_AVATAR_UPLOAD_BYTES = 5 * 1024 * 1024

type AvatarSourceError =
  | 'unsupportedFormat'
  | 'sourceTooLarge'
  | 'signatureMismatch'
  | 'decodeError'
  | 'dimensionsTooLarge'
  | 'processingError'

interface AvatarOffset {
  x: number
  y: number
}

interface AvatarCropLayout {
  scale: number
  maxOffsetX: number
  maxOffsetY: number
}

interface AvatarCropRect {
  sourceX: number
  sourceY: number
  sourceSize: number
}

const mimeByExtension: Readonly<Record<string, string>> = {
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
}

function detectedMimeType(bytes: Uint8Array): string | null {
  if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return 'image/jpeg'
  if (
    bytes[0] === 0x89 &&
    bytes[1] === 0x50 &&
    bytes[2] === 0x4e &&
    bytes[3] === 0x47 &&
    bytes[4] === 0x0d &&
    bytes[5] === 0x0a &&
    bytes[6] === 0x1a &&
    bytes[7] === 0x0a
  )
    return 'image/png'
  if (
    bytes[0] === 0x52 &&
    bytes[1] === 0x49 &&
    bytes[2] === 0x46 &&
    bytes[3] === 0x46 &&
    bytes[8] === 0x57 &&
    bytes[9] === 0x45 &&
    bytes[10] === 0x42 &&
    bytes[11] === 0x50
  )
    return 'image/webp'
  return null
}

async function validateAvatarSourceFile(file: File): Promise<AvatarSourceError | null> {
  const extension = file.name.split('.').pop()?.toLowerCase() ?? ''
  const expectedMime = mimeByExtension[extension]
  if (!expectedMime || file.type.toLowerCase() !== expectedMime) return 'unsupportedFormat'
  if (file.size === 0) return 'decodeError'
  if (file.size > MAX_AVATAR_SOURCE_BYTES) return 'sourceTooLarge'

  try {
    const header = new Uint8Array(await file.slice(0, 12).arrayBuffer())
    return detectedMimeType(header) === expectedMime ? null : 'signatureMismatch'
  } catch {
    return 'decodeError'
  }
}

function validateAvatarSourceDimensions(width: number, height: number): AvatarSourceError | null {
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0)
    return 'decodeError'
  if (
    width > MAX_AVATAR_SOURCE_DIMENSION ||
    height > MAX_AVATAR_SOURCE_DIMENSION ||
    width * height > MAX_AVATAR_SOURCE_PIXELS
  )
    return 'dimensionsTooLarge'
  return null
}

function avatarCropLayout(
  sourceWidth: number,
  sourceHeight: number,
  viewportSize: number,
  zoom: number,
): AvatarCropLayout {
  const scale = Math.max(viewportSize / sourceWidth, viewportSize / sourceHeight) * zoom
  return {
    scale,
    maxOffsetX: Math.max(0, (sourceWidth * scale - viewportSize) / 2),
    maxOffsetY: Math.max(0, (sourceHeight * scale - viewportSize) / 2),
  }
}

function clampAvatarOffset(offset: AvatarOffset, layout: AvatarCropLayout): AvatarOffset {
  return {
    x: Math.min(layout.maxOffsetX, Math.max(-layout.maxOffsetX, offset.x)),
    y: Math.min(layout.maxOffsetY, Math.max(-layout.maxOffsetY, offset.y)),
  }
}

function avatarCropRect(
  sourceWidth: number,
  sourceHeight: number,
  viewportSize: number,
  zoom: number,
  offset: AvatarOffset,
): AvatarCropRect {
  const layout = avatarCropLayout(sourceWidth, sourceHeight, viewportSize, zoom)
  const safeOffset = clampAvatarOffset(offset, layout)
  const sourceSize = viewportSize / layout.scale
  return {
    sourceX: (sourceWidth - sourceSize) / 2 - safeOffset.x / layout.scale,
    sourceY: (sourceHeight - sourceSize) / 2 - safeOffset.y / layout.scale,
    sourceSize,
  }
}

function canvasBlob(canvas: HTMLCanvasElement, type: string, quality?: number) {
  return new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, type, quality))
}

async function createCroppedAvatarFile(
  image: HTMLImageElement,
  viewportSize: number,
  zoom: number,
  offset: AvatarOffset,
): Promise<File> {
  const canvas = document.createElement('canvas')
  canvas.width = AVATAR_OUTPUT_SIZE
  canvas.height = AVATAR_OUTPUT_SIZE
  const context = canvas.getContext('2d')
  if (!context) throw new Error('Avatar canvas is unavailable.')

  const crop = avatarCropRect(image.naturalWidth, image.naturalHeight, viewportSize, zoom, offset)
  context.imageSmoothingEnabled = true
  context.imageSmoothingQuality = 'high'
  context.drawImage(
    image,
    crop.sourceX,
    crop.sourceY,
    crop.sourceSize,
    crop.sourceSize,
    0,
    0,
    AVATAR_OUTPUT_SIZE,
    AVATAR_OUTPUT_SIZE,
  )

  let blob = await canvasBlob(canvas, 'image/webp', 0.88)
  let extension = 'webp'
  if (!blob || blob.type !== 'image/webp') {
    blob = await canvasBlob(canvas, 'image/png')
    extension = 'png'
  }
  if (!blob || blob.size === 0 || blob.size > MAX_AVATAR_UPLOAD_BYTES)
    throw new Error('Avatar output could not be encoded within the upload limit.')

  return new File([blob], `avatar.${extension}`, {
    type: blob.type,
    lastModified: Date.now(),
  })
}

export {
  AVATAR_ACCEPT,
  AVATAR_OUTPUT_SIZE,
  MAX_AVATAR_SOURCE_BYTES,
  MAX_AVATAR_SOURCE_DIMENSION,
  MAX_AVATAR_SOURCE_PIXELS,
  avatarCropLayout,
  avatarCropRect,
  clampAvatarOffset,
  createCroppedAvatarFile,
  validateAvatarSourceDimensions,
  validateAvatarSourceFile,
}
export type { AvatarCropLayout, AvatarOffset, AvatarSourceError }
