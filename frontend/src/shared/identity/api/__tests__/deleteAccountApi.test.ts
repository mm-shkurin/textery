import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { deletionConfirmationKind, requestAccountDeletion } from '../deleteAccountApi'
import { DeletionRejectedError } from '../profileErrors'
import type { Profile } from '../profileWire'
import {
  clearSession,
  getAccessToken,
  saveSession,
} from '../../../../features/auth/utils/authSession'

// The one irreversible operation in the product. Two things are asserted here that nothing else
// can: which field goes on the wire for which kind of account, and that a refused confirmation
// leaves the session — and what the user typed — exactly where they were.

function profileWith(hasPassword: boolean | null | undefined): Profile {
  return {
    email: 'ada@example.ru',
    name: null,
    createdAt: '2025-02-03T09:26:53Z',
    avatarUpdatedAt: null,
    hasPassword,
  }
}

function noContent() {
  return { ok: true, status: 204, json: async () => ({}) }
}

function rejected(body: unknown, code = 400) {
  return { ok: false, status: code, json: async () => body }
}

function lastCall(fetchMock: ReturnType<typeof vi.fn>) {
  return fetchMock.mock.calls[fetchMock.mock.calls.length - 1]
}

describe('which proof this account can give', () => {
  it('asks for a password only when the backend said there is one', () => {
    expect(deletionConfirmationKind(profileWith(true))).toBe('password')
  })

  // Both ways of being wrong are not equal. An address field shown to somebody who has a password
  // costs one readable 400 with the session intact; a password field shown to somebody with no
  // password is a dead end inside the product. So every uncertain case takes the recoverable one.
  it.each([[false], [null], [undefined]])(
    'falls back to the address when has_password is %s',
    (flag) => {
      expect(deletionConfirmationKind(profileWith(flag as boolean | null))).toBe('email')
    },
  )
})

describe('sending the confirmation', () => {
  beforeEach(() => saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' }))
  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('POSTs to the deletion sub-resource', async () => {
    const fetchMock = vi.fn().mockResolvedValue(noContent())
    vi.stubGlobal('fetch', fetchMock)

    await requestAccountDeletion({ kind: 'password', password: 'Str0ng!Pass' })

    const [url, options] = lastCall(fetchMock)
    expect(String(url)).toContain('/api/v1/auth/me/deletion')
    expect(options.method).toBe('POST')
  })

  it('sends only the password field for a password account', async () => {
    const fetchMock = vi.fn().mockResolvedValue(noContent())
    vi.stubGlobal('fetch', fetchMock)

    await requestAccountDeletion({ kind: 'password', password: 'Str0ng!Pass' })

    expect(JSON.parse(lastCall(fetchMock)[1].body)).toEqual({ password: 'Str0ng!Pass' })
  })

  it('sends only the address field, under the name the backend reads', async () => {
    const fetchMock = vi.fn().mockResolvedValue(noContent())
    vi.stubGlobal('fetch', fetchMock)

    await requestAccountDeletion({ kind: 'email', email: 'ada@example.ru' })

    expect(JSON.parse(lastCall(fetchMock)[1].body)).toEqual({ confirm_email: 'ada@example.ru' })
  })

  it('expects nothing back from a 204', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(noContent()))

    await expect(
      requestAccountDeletion({ kind: 'password', password: 'Str0ng!Pass' }),
    ).resolves.toBeUndefined()
  })
})

describe('when the confirmation does not match', () => {
  beforeEach(() => saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' }))
  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('reports the refusal with the message the backend wrote', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        rejected({
          error_code: 'DELETION_CONFIRMATION_INVALID',
          message: 'Подтверждение не совпало. Ничего не удалено.',
        }),
      ),
    )

    await expect(
      requestAccountDeletion({ kind: 'password', password: 'wrong' }),
    ).rejects.toMatchObject({
      name: 'DeletionRejectedError',
      message: 'Подтверждение не совпало. Ничего не удалено.',
    })
  })

  it('falls back to its own wording when the 400 carries no message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({})))

    await expect(
      requestAccountDeletion({ kind: 'email', email: 'nobody@example.ru' }),
    ).rejects.toMatchObject({ message: 'Подтверждение не принято. Проверьте введённое.' })
  })

  it('leaves the session alive, so the user stays on the screen', async () => {
    // Emphatically not a session ending: the tokens are untouched and what was typed is still
    // there to correct.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({ message: 'нет' })))

    await expect(requestAccountDeletion({ kind: 'password', password: 'wrong' })).rejects.toThrow()
    expect(getAccessToken()).toBe('access-1')
  })

  it.each([403, 500])(
    'lets a %i through as itself rather than a confirmation refusal',
    async (code) => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(rejected({ message: 'nope' }, code)))

      await expect(
        requestAccountDeletion({ kind: 'password', password: 'Str0ng!Pass' }),
      ).rejects.not.toBeInstanceOf(DeletionRejectedError)
    },
  )
})
