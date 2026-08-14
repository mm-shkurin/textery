import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AVATAR_EDGE_PX, resizeAvatar } from '../utils/avatarImage'
import { stubObjectUrls } from './avatarTestSupport'
import { partialDouble } from '../../../test/doubles'

// The two ways this can go wrong at runtime, split from `avatarImage.test.ts` for the
// 200-line cap. Both are about a promise that must REJECT: a resizer that neither
// resolves nor rejects leaves the upload button spinning with nothing to report, and
// no amount of retrying gets the user out of it.

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
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(partialDouble<CanvasRenderingContext2D>({
      drawImage: vi.fn(),
    }))
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((callback: BlobCallback) => {
      callback(null)
    })

    await expect(resizeAvatar(aFile())).rejects.toThrow('avatar: encode failed')
  })
})
