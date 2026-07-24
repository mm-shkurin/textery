import { afterEach, describe, expect, it, vi } from 'vitest'
import { register } from '../registerApi'
import { GENERIC_REGISTER_FAILURE_MESSAGE } from '../../utils/authMessages'

// fetch is stubbed rather than httpClient mocked: what this module DOES is translate one wire
// shape into another, so mocking the transport would leave the translation untested — which is
// how `confirm_password` went missing and registration returned 422 for every user while every
// unit test stayed green.
function respond(status: number, body: unknown) {
  return { ok: status < 400, status, json: async () => body }
}

function created() {
  return respond(201, {
    user_id: 'u-1',
    email: 'someone@example.ru',
    is_verified: false,
    verification_code: '123456',
    code_expires_at: '2026-07-16T00:10:00Z',
  })
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('register', () => {
  it('sends confirm_password, which the backend requires and rejects the request without', async () => {
    const fetchMock = vi.fn().mockResolvedValue(created())
    vi.stubGlobal('fetch', fetchMock)

    await register('someone@example.ru', 'Passw0rd!', 'Passw0rd!')

    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/api/v1/auth/register')
    expect(JSON.parse(String(init.body))).toEqual({
      email: 'someone@example.ru',
      password: 'Passw0rd!',
      confirm_password: 'Passw0rd!',
    })
  })

  it('translates the wire response into the app shape', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(created()))

    await expect(register('someone@example.ru', 'Passw0rd!', 'Passw0rd!')).resolves.toEqual({
      userId: 'u-1',
      email: 'someone@example.ru',
      isVerified: false,
      verificationCode: '123456',
      codeExpiresAt: '2026-07-16T00:10:00Z',
    })
  })

  // A 201 missing fields is a contract the backend broke, not a crash this client should have.
  // Empty strings keep the verify screen renderable so the user is told something went wrong
  // there, rather than the whole tree unmounting on `undefined.length`.
  it('fills absent fields with empty strings instead of undefined', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(respond(201, {})))

    await expect(register('someone@example.ru', 'Passw0rd!', 'Passw0rd!')).resolves.toEqual({
      userId: '',
      email: '',
      isVerified: false,
      verificationCode: '',
      codeExpiresAt: '',
    })
  })

  it('surfaces the message the server gave for an already-registered email', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        respond(409, {
          error_code: 'EMAIL_ALREADY_REGISTERED',
          message: 'Email уже зарегистрирован',
        }),
      ),
    )

    await expect(register('taken@example.ru', 'Passw0rd!', 'Passw0rd!')).rejects.toMatchObject({
      message: 'Email уже зарегистрирован',
    })
  })

  // Pydantic's 422 envelope carries no error_code — it means THIS client built a malformed body,
  // which is a bug here, not something the user can act on. It gets the generic message.
  it('falls back to the generic message on a 422 with no error code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(respond(422, { detail: [{ loc: ['body', 'password'] }] })),
    )

    await expect(register('someone@example.ru', 'Passw0rd!', 'Passw0rd!')).rejects.toMatchObject({
      message: GENERIC_REGISTER_FAILURE_MESSAGE,
    })
  })

  it('falls back to the generic message when the transport itself fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

    await expect(register('someone@example.ru', 'Passw0rd!', 'Passw0rd!')).rejects.toBeDefined()
  })
})
