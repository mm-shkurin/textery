import { vi } from 'vitest'
import type { Profile } from '../../../shared/identity/api/profileApi'

// jsdom implements neither object URLs nor a canvas, and both are load-bearing here: the picture
// reaches the <img> as an object URL, and the upload path decodes and re-encodes through a canvas.
// Stubbing them is what lets these tests assert the SEAMS — how many requests are made, what is
// sent — which is where the bugs in this feature live. What a real encoder produces is the
// browser's business and is not asserted.

export function profileWith(overrides: Partial<Profile> = {}): Profile {
  return {
    email: 'anna.ivanova@example.com',
    name: 'Анна Ковалёва',
    createdAt: '2025-02-03T09:26:53Z',
    avatarUpdatedAt: null,
    ...overrides,
  }
}

export function stubObjectUrls(): { created: string[]; revoked: string[] } {
  const created: string[] = []
  const revoked: string[] = []
  vi.stubGlobal('URL', {
    ...URL,
    createObjectURL: vi.fn(() => {
      const url = `blob:avatar-${created.length + 1}`
      created.push(url)
      return url
    }),
    revokeObjectURL: vi.fn((url: string) => {
      revoked.push(url)
    }),
  })
  return { created, revoked }
}

export interface EncodedCanvas {
  width: number
  height: number
  type: string
  quality: number
}

// A decoder and an encoder that do nothing but record their arguments. The encoded result is a
// fixed, deliberately TINY blob: the assertion that matters is that what leaves the browser is
// the encoder's output rather than the file the user picked.
export function stubCanvasPipeline(source: { width: number; height: number }): EncodedCanvas[] {
  const encoded: EncodedCanvas[] = []
  vi.stubGlobal(
    'createImageBitmap',
    vi.fn(async () => source),
  )
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
    drawImage: vi.fn(),
  } as unknown as CanvasRenderingContext2D)
  vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation(function (
    this: HTMLCanvasElement,
    callback: BlobCallback,
    type?: string,
    quality?: number,
  ) {
    encoded.push({
      width: this.width,
      height: this.height,
      type: type ?? '',
      quality: quality ?? 0,
    })
    callback(new Blob([new Uint8Array(20_480)], { type: 'image/webp' }))
  })
  return encoded
}
