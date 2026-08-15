import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { NameRejectedError, fetchProfile, saveProfileName } from '../profileApi'
import { clearSession, saveSession } from '../../../../features/auth/utils/authSession'

// `GET` and `PATCH /api/v1/auth/me` against a stubbed transport. The subject is the wire→app
// boundary: what is sent, and what a response is turned into. The rename in particular answers
// with the NORMALIZED name rather than an echo, and a caller that recomputed "unsaved" against
// what it sent would show a name with a trailing space as dirty forever.

const WIRE_PROFILE = {
  email: 'ada@example.ru',
  name: 'Ада Лавлейс',
  created_at: '2025-02-03T09:26:53Z',
  avatar_updated_at: '2026-08-13T10:00:00Z',
  has_password: true,
}

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body }
}

function rejected(body: unknown, code = 400) {
  return { ok: false, status: code, json: async () => body }
}

function lastCall(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls[fetchMock.mock.calls.length - 1]
}

describe('reading the profile', () => {
  beforeEach(() => saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' }))
  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('maps the wire shape into the app shape', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok(WIRE_PROFILE)))

    expect(await fetchProfile()).toEqual({
      email: 'ada@example.ru',
      name: 'Ада Лавлейс',
      createdAt: '2025-02-03T09:26:53Z',
      avatarUpdatedAt: '2026-08-13T10:00:00Z',
      hasPassword: true,
    })
  })

  it('reads a null name as no name', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, name: null })))

    expect((await fetchProfile()).name).toBeNull()
  })

  it('reads an empty name as no name too', async () => {
    // Both are "this account has no display name"; the header's email fallback keys on one value.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, name: '' })))

    expect((await fetchProfile()).name).toBeNull()
  })

  it('reads a missing avatar timestamp as no picture', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, avatar_updated_at: null })),
    )

    expect((await fetchProfile()).avatarUpdatedAt).toBeNull()
  })

  it('keeps an absent has_password as null rather than coercing it to false', async () => {
    // `Boolean(undefined)` and a genuine `false` would become the same value, and one of them is
    // a fact while the other is an absence. The deletion screen branches on that difference.
    const { has_password: _omitted, ...withoutFlag } = WIRE_PROFILE
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok(withoutFlag)))

    expect((await fetchProfile()).hasPassword).toBeNull()
  })

  it('keeps a non-boolean has_password as null', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, has_password: 'yes' })))

    expect((await fetchProfile()).hasPassword).toBeNull()
  })

  it('carries a genuine false through', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, has_password: false })))

    expect((await fetchProfile()).hasPassword).toBe(false)
  })

  it('falls back to empty strings for fields the response did not carry', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(ok({})))

    expect(await fetchProfile()).toEqual({
      email: '',
      name: null,
      createdAt: '',
      avatarUpdatedAt: null,
      hasPassword: null,
    })
  })
})

describe('renaming', () => {
  beforeEach(() => saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' }))
  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('PATCHes the name to the one profile path', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(WIRE_PROFILE))
    vi.stubGlobal('fetch', fetchMock)

    await saveProfileName('Ада Лавлейс')

    const [url, options] = lastCall(fetchMock)
    expect(String(url)).toContain('/api/v1/auth/me')
    expect(options.method).toBe('PATCH')
    expect(JSON.parse(options.body)).toEqual({ name: 'Ада Лавлейс' })
  })

  it('sends an empty string rather than an empty body to clear the name', async () => {
    // `{}` would mean "leave the name alone" — the opposite instruction.
    const fetchMock = vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, name: null }))
    vi.stubGlobal('fetch', fetchMock)

    await saveProfileName('')

    expect(JSON.parse(lastCall(fetchMock)[1].body)).toEqual({ name: '' })
  })

  it('answers with the normalized name from the response, not the value sent', async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok({ ...WIRE_PROFILE, name: 'Ада' }))
    vi.stubGlobal('fetch', fetchMock)

    expect((await saveProfileName('  Ада  ')).name).toBe('Ада')
  })

  it('turns a 400 into a rejection the field can render', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(rejected({ error_code: 'INVALID_NAME', message: 'Имя не подходит.' })),
    )

    await expect(saveProfileName('x'.repeat(61))).rejects.toMatchObject({
      name: 'NameRejectedError',
      errorCode: 'INVALID_NAME',
      message: 'Имя не подходит.',
    })
  })

  it('falls back to a readable code and message when the 400 carries neither', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({})))

    await expect(saveProfileName('x')).rejects.toMatchObject({
      errorCode: 'INVALID_NAME',
      message: 'Имя не принято.',
    })
  })

  it('falls back when the 400 carries an empty message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({ message: '' })))

    await expect(saveProfileName('x')).rejects.toMatchObject({ message: 'Имя не принято.' })
  })

  it.each([401, 404, 500])(
    'lets a %i through as itself rather than a name rejection',
    async (code) => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({ message: 'nope' }, code)))

      await expect(saveProfileName('Ада')).rejects.not.toBeInstanceOf(NameRejectedError)
    },
  )
})
