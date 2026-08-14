import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ALLOWED_AVATAR_TYPES,
  AVATAR_EDGE_PX,
  MAX_AVATAR_SOURCE_BYTES,
  avatarFileRejection,
  resizeAvatar,
} from '../utils/avatarImage'
import { stubObjectUrls } from './avatarTestSupport'
import { partialDouble } from '../../../test/doubles'

// The module itself, not through the page. Everything that stands between a 12-megapixel
// photograph and the request body lives here — the decode, the crop, the encode, and the object
// URL that has to be released whichever way the decode ends. The page-level tests exercise the
// happy seam; these cover the branches only a direct call can reach, including the fallback
// decoder that no current browser takes and the three failures that must surface as a rejected
// promise rather than one that never settles.

interface DrawCall {
  args: number[]
}

function stubDecoderReturning(source: { width: number; height: number }) {
  vi.stubGlobal(
    'createImageBitmap',
    vi.fn(async () => source),
  )
}

function stubCanvas(): { draws: DrawCall[]; sizes: { width: number; height: number }[] } {
  const draws: DrawCall[] = []
  const sizes: { width: number; height: number }[] = []
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(
    partialDouble<CanvasRenderingContext2D>({
      drawImage: vi.fn((_source: unknown, ...args: number[]) => {
        draws.push({ args })
      }),
    }),
  )
  vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation(function (
    this: HTMLCanvasElement,
    callback: BlobCallback,
  ) {
    sizes.push({ width: this.width, height: this.height })
    callback(new Blob([new Uint8Array(2048)], { type: 'image/webp' }))
  })
  return { draws, sizes }
}

function aFile(type = 'image/jpeg', size = 1024): File {
  return new File([new Uint8Array(size)], 'photo', { type })
}

describe('what the user is allowed to pick', () => {
  it.each(ALLOWED_AVATAR_TYPES)('accepts %s', (type) => {
    expect(avatarFileRejection(aFile(type))).toBeNull()
  })

  // SVG is out of the `accept` attribute AND out of this check, because `accept` is a hint the
  // file dialog may ignore — and an avatar is displayed on every authenticated page.
  it.each(['image/svg+xml', 'image/gif', 'image/bmp', 'application/pdf', 'text/plain', ''])(
    'refuses %s naming the formats that would work',
    (type) => {
      expect(avatarFileRejection(aFile(type))).toBe(
        'Подойдёт PNG, JPEG или WebP — этот формат загрузить нельзя.',
      )
    },
  )

  it('accepts a file exactly on the size bound', () => {
    expect(avatarFileRejection(aFile('image/png', MAX_AVATAR_SOURCE_BYTES))).toBeNull()
  })

  it('refuses a file one byte over it', () => {
    expect(avatarFileRejection(aFile('image/png', MAX_AVATAR_SOURCE_BYTES + 1))).toBe(
      'Файл больше 10 МБ — выберите изображение поменьше.',
    )
  })

  it('refuses on the format before the size, so an oversized SVG is not called too big', () => {
    const rejection = avatarFileRejection(aFile('image/svg+xml', MAX_AVATAR_SOURCE_BYTES + 1))

    expect(rejection).toContain('этот формат')
  })
})

describe('resizing', () => {
  beforeEach(() => {
    stubObjectUrls()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('shrinks a large picture to the target edge', async () => {
    stubDecoderReturning({ width: 3024, height: 3024 })
    const { sizes } = stubCanvas()

    const resized = await resizeAvatar(aFile('image/jpeg', 4 * 1024 * 1024))

    expect(sizes).toEqual([{ width: AVATAR_EDGE_PX, height: AVATAR_EDGE_PX }])
    expect(resized.size).toBeLessThan(4 * 1024 * 1024)
  })

  it('takes a centred square out of a portrait rather than squashing it', async () => {
    // A full-frame draw into a square canvas would deform the face. The source rectangle has to
    // be square and centred; the destination is the whole canvas.
    stubDecoderReturning({ width: 3024, height: 4032 })
    const { draws, sizes } = stubCanvas()

    await resizeAvatar(aFile())

    expect(draws[0].args).toEqual([0, 504, 3024, 3024, 0, 0, AVATAR_EDGE_PX, AVATAR_EDGE_PX])
    expect(sizes).toEqual([{ width: AVATAR_EDGE_PX, height: AVATAR_EDGE_PX }])
  })

  it('takes a centred square out of a landscape too', async () => {
    stubDecoderReturning({ width: 4032, height: 3024 })
    const { draws } = stubCanvas()

    await resizeAvatar(aFile())

    expect(draws[0].args).toEqual([504, 0, 3024, 3024, 0, 0, AVATAR_EDGE_PX, AVATAR_EDGE_PX])
  })

  it('never upscales a picture smaller than the target', async () => {
    // Blowing a 64px picture up to 256 costs bytes to add blur.
    stubDecoderReturning({ width: 64, height: 64 })
    const { draws, sizes } = stubCanvas()

    await resizeAvatar(aFile())

    expect(sizes).toEqual([{ width: 64, height: 64 }])
    expect(draws[0].args).toEqual([0, 0, 64, 64, 0, 0, 64, 64])
  })

  it('sizes the canvas by the SHORTER side of a small non-square picture', async () => {
    stubDecoderReturning({ width: 200, height: 80 })
    const { sizes } = stubCanvas()

    await resizeAvatar(aFile())

    expect(sizes).toEqual([{ width: 80, height: 80 }])
  })
})
