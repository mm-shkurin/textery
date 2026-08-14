import { browserDocument } from '../../../shared/lib/browser'
// Validation and downscaling, both on the CLIENT, both before a single byte is uploaded.
//
// The server stores the bytes and does not decode them — decided, not an oversight — so nothing
// downstream will shrink a photograph. Without this module the feature does not work at all: any
// picture off a phone camera is 3–8 MB and every upload would be refused as too large. A 4 MB
// source leaves here at roughly 20 KB.
//
// SVG is refused everywhere: it is not an image the way the others are, it is a document that can
// carry script, and an avatar is displayed on every authenticated page. It is out of the `accept`
// attribute AND out of the check below, because `accept` is a hint the file dialog may ignore.
export const ALLOWED_AVATAR_TYPES = ['image/png', 'image/jpeg', 'image/webp']

// The bound on what the user may PICK, not on what is sent. Generous on purpose: everything under
// it is downscaled to ~20 KB anyway, and the only job of this number is to stop the browser
// decoding something absurd into memory.
export const MAX_AVATAR_SOURCE_BYTES = 10 * 1024 * 1024

export const AVATAR_EDGE_PX = 256
const AVATAR_MIME = 'image/webp'
const AVATAR_QUALITY = 0.85

export function avatarFileRejection(file: File): string | null {
  if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
    return 'Подойдёт PNG, JPEG или WebP — этот формат загрузить нельзя.'
  }
  if (file.size > MAX_AVATAR_SOURCE_BYTES) {
    return 'Файл больше 10 МБ — выберите изображение поменьше.'
  }
  return null
}

// `createImageBitmap` decodes off the main thread and is what every current browser has. The
// <img> fallback exists for the ones that do not, and revokes its own URL either way — an object
// URL that outlives the decode is a leak per attempted upload.
async function decode(file: File): Promise<CanvasImageSource & { width: number; height: number }> {
  if (typeof createImageBitmap === 'function') {
    return await createImageBitmap(file)
  }
  const objectUrl = URL.createObjectURL(file)
  try {
    return await new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = () => reject(new Error('avatar: decode failed'))
      image.src = objectUrl
    })
  } finally {
    URL.revokeObjectURL(objectUrl)
  }
}

// A CENTRAL SQUARE CROP, in one `drawImage`: the largest square the picture contains, taken from
// its middle, painted into the whole canvas. Aspect ratio is preserved because source and
// destination are both square — a plain full-frame draw into a square canvas would squash a
// portrait into a face nobody would recognise.
//
// Never UPSCALED: a 64px picture stays 64px rather than being blown up to 256 and re-encoded,
// which costs bytes to add blur.
export async function resizeAvatar(file: File): Promise<Blob> {
  const source = await decode(file)
  const sourceEdge = Math.min(source.width, source.height)
  const edge = Math.min(AVATAR_EDGE_PX, sourceEdge)

  const doc = browserDocument()
  if (!doc) throw new Error('Изображение можно обработать только в браузере.')
  const canvas = doc.createElement('canvas')
  canvas.width = edge
  canvas.height = edge
  const context = canvas.getContext('2d')
  if (context === null) throw new Error('avatar: no 2d context')
  context.drawImage(
    source,
    (source.width - sourceEdge) / 2,
    (source.height - sourceEdge) / 2,
    sourceEdge,
    sourceEdge,
    0,
    0,
    edge,
    edge,
  )

  return await new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        // `toBlob` hands back null when the encoder fails or the type is unsupported. Uploading a
        // null would become the string "null" on the wire.
        if (blob === null) reject(new Error('avatar: encode failed'))
        else resolve(blob)
      },
      AVATAR_MIME,
      AVATAR_QUALITY,
    )
  })
}
