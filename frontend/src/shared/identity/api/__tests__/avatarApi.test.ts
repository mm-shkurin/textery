import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AvatarRejectedError } from '../profileErrors'
import { deleteAvatar, fetchAvatarBytes, uploadAvatar } from '../avatarApi'
import { clearSession, getAccessToken, saveSession } from '../../../session/authSession'

// Two things decide the shape of this file. The bytes go in the body RAW — anything httpClient
// does not recognise as a Blob is JSON-stringified into the string "{}" — and the three calls do
// NOT share a failure policy: the GET fires unprompted on page load and must never end the
// session, while the PUT and the DELETE are user-initiated and must report a dead one honestly.

const WIRE_PROFILE = {
  email: 'ada@example.ru',
  name: null,
  created_at: '2025-02-03T09:26:53Z',
  avatar_updated_at: '2026-08-13T10:00:00Z',
  has_password: true,
}

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body }
}

function okBlob(blob: Blob) {
  return { ok: true, status: 200, blob: async () => blob, json: async () => ({}) }
}

function rejected(body: unknown, code = 400) {
  return { ok: false, status: code, json: async () => body }
}

function lastCall(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls[fetchMock.mock.calls.length - 1]
}

describe('uploading the image', () => {
  beforeEach(() => saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' }))
  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('PUTs the blob itself as the body', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(WIRE_PROFILE))
    vi.stubGlobal('fetch', fetchMock)
    const bytes = new Blob([new Uint8Array(2048)], { type: 'image/webp' })

    await uploadAvatar(bytes)

    const [url, options] = lastCall(fetchMock)
    expect(String(url)).toContain('/api/v1/auth/me/avatar')
    expect(options.method).toBe('PUT')
    expect(options.body).toBe(bytes)
  })

  it('declares the type the client actually encoded to', async () => {
    // The server stores bytes and does not decode them, so this header is the only statement of
    // what they are on the way in.
    const fetchMock = vi.fn().mockResolvedValue(ok(WIRE_PROFILE))
    vi.stubGlobal('fetch', fetchMock)

    await uploadAvatar(new Blob([new Uint8Array(8)], { type: 'image/webp' }))

    expect(lastCall(fetchMock)[1].headers['Content-Type']).toBe('image/webp')
  })

  it('answers with the profile the upload response carried', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok(WIRE_PROFILE)))

    expect((await uploadAvatar(new Blob([]))).avatarUpdatedAt).toBe('2026-08-13T10:00:00Z')
  })

  it('turns a 400 into a rejection that can be shown beside the picture', async () => {
    // A different class from the name's refusal on purpose: one `catch` that could not tell them
    // apart would put an image complaint under the name field.
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        rejected({
          error_code: 'AVATAR_DIMENSIONS_TOO_LARGE',
          message: 'Изображение слишком большое.',
        }),
      ),
    )

    await expect(uploadAvatar(new Blob([]))).rejects.toMatchObject({
      name: 'AvatarRejectedError',
      errorCode: 'AVATAR_DIMENSIONS_TOO_LARGE',
      message: 'Изображение слишком большое.',
    })
  })

  it('falls back to a readable code and message when the 400 carries neither', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({})))

    await expect(uploadAvatar(new Blob([]))).rejects.toMatchObject({
      errorCode: 'AVATAR_UNSUPPORTED_TYPE',
      message: 'Изображение не принято.',
    })
  })

  it.each([413, 500])('lets a %i through as itself', async (code) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({ message: 'nope' }, code)))

    await expect(uploadAvatar(new Blob([]))).rejects.not.toBeInstanceOf(AvatarRejectedError)
  })
})

describe('removing the image', () => {
  beforeEach(() => saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' }))
  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('DELETEs and answers with the profile reporting no picture', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, avatar_updated_at: null }))
    vi.stubGlobal('fetch', fetchMock)

    const profile = await deleteAvatar()

    expect(lastCall(fetchMock)[1].method).toBe('DELETE')
    expect(profile.avatarUpdatedAt).toBeNull()
  })

  it('sends no body with the deletion', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(WIRE_PROFILE))
    vi.stubGlobal('fetch', fetchMock)

    await deleteAvatar()

    expect(lastCall(fetchMock)[1].body).toBeUndefined()
  })
})

describe('fetching the bytes', () => {
  beforeEach(() => saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' }))
  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('asks for a blob with the token attached', async () => {
    // The image cannot be shown with `<img src="...">`: the browser attaches no Authorization
    // header, the endpoint answers 401, and every user gets a broken image.
    const bytes = new Blob([new Uint8Array(16)], { type: 'image/webp' })
    const fetchMock = vi.fn().mockResolvedValue(okBlob(bytes))
    vi.stubGlobal('fetch', fetchMock)

    expect(await fetchAvatarBytes()).toBe(bytes)
    expect(lastCall(fetchMock)[1].headers.Authorization).toBe('Bearer access-1')
  })

  it('leaves the session alone when the image read fails', async () => {
    // It fires on page load, unprompted. A 5xx here must not sign anybody out.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({}, 503)))

    await expect(fetchAvatarBytes()).rejects.toThrow('Данные учётной записи сейчас недоступны.')
    expect(getAccessToken()).toBe('access-1')
  })

  it('leaves the session alone on a 404 from an account whose picture is gone', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({}, 404)))

    await expect(fetchAvatarBytes()).rejects.toThrow()
    expect(getAccessToken()).toBe('access-1')
  })
})
