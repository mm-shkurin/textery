import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  ALLOWED_AVATAR_TYPES,
  AVATAR_EDGE_PX,
  MAX_AVATAR_SOURCE_BYTES,
  avatarFileRejection,
  resizeAvatar,
} from '../avatarImage'
import { stubObjectUrls } from './avatarTestSupport'

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
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
    drawImage: vi.fn((_source: unknown, ...args: number[]) => {
      draws.push({ args })
    }),
  } as unknown as CanvasRenderingContext2D)
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

describe('the fallback decoder, for browsers without createImageBitmap', () => {
  let urls: { created: string[]; revoked: string[] }

  beforeEach(() => {
    urls = stubObjectUrls()
    vi.stubGlobal('createImageBitmap', undefined)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  function stubImage(outcome: 'load' | 'error') {
    class StubImage {
      width = 512
      height = 512
      onload: (() => void) | null = null
      onerror: (() => void) | null = null
      set src(_value: string) {
        queueMicrotask(() => (outcome === 'load' ? this.onload?.() : this.onerror?.()))
      }
    }
    vi.stubGlobal('Image', StubImage)
  }

  it('decodes through an <img> and releases the object URL it made', async () => {
    stubImage('load')
    const { sizes } = stubCanvas()

    await resizeAvatar(aFile())

    expect(sizes).toEqual([{ width: AVATAR_EDGE_PX, height: AVATAR_EDGE_PX }])
    expect(urls.revoked).toEqual(urls.created)
  })

  it('rejects a file the browser cannot decode instead of hanging', async () => {
    // A promise that never settles leaves the button spinning with nothing to report.
    stubImage('error')
    stubCanvas()

    await expect(resizeAvatar(aFile())).rejects.toThrow('avatar: decode failed')
  })

  it('releases the object URL on a failed decode too', async () => {
    // One leaked URL per attempted upload, and a retry loop is exactly when it happens.
    stubImage('error')
    stubCanvas()

    await expect(resizeAvatar(aFile())).rejects.toThrow()

    expect(urls.created).toHaveLength(1)
    expect(urls.revoked).toEqual(urls.created)
  })
})

describe('when the browser cannot finish the job', () => {
  beforeEach(() => {
    stubObjectUrls()
    stubDecoderReturning({ width: 512, height: 512 })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('reports a canvas it could not get a context for', async () => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null)

    await expect(resizeAvatar(aFile())).rejects.toThrow('avatar: no 2d context')
  })

  it('reports an encoder that handed back nothing', async () => {
    // `toBlob` yields null when the encoder fails or the type is unsupported; uploading that
    // would put the string "null" on the wire.
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      drawImage: vi.fn(),
    } as unknown as CanvasRenderingContext2D)
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback: BlobCallback) => {
      callback(null)
    })

    await expect(resizeAvatar(aFile())).rejects.toThrow('avatar: encode failed')
  })
})
