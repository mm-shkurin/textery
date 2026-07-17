import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createDocument } from '../documentApi'
import { VersionConflictError } from '../../../../shared/api/send'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// 409 is not one thing, and `send` used to pretend it was — it mapped the bare STATUS to
// VersionConflictError. `saveDocument`'s 409 does mean a stale version, but `createDocument`
// carries an Idempotency-Key and can 409 over the key itself: an operation with no version at
// all. A user whose create collided was told "Документ был изменён другим сохранением" — a
// lost-update message for a document that had never been saved once, sending them to reopen
// something that does not exist. The carve-out matches on error_code now.
describe('documentApi createDocument — a 409 that is not a version conflict', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('does not report an idempotency-key conflict as a lost update', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({
          error_code: 'IDEMPOTENCY_KEY_CONFLICT',
          message: 'Ключ идемпотентности уже использован с другими параметрами',
        }),
      }),
    )

    const rejection = await createDocument('doklad', 'key-1').catch((error: unknown) => error)

    // Not the version-conflict type: nothing here is recoverable by refetching a version.
    expect(rejection).not.toBeInstanceOf(VersionConflictError)
    // The server's own message survives — it names what actually happened.
    expect((rejection as Error).message).toBe(
      'Ключ идемпотентности уже использован с другими параметрами',
    )
  })

  it('still raises VersionConflictError for a 409 that says VERSION_CONFLICT', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ error_code: 'VERSION_CONFLICT', message: 'conflict' }),
      }),
    )

    const rejection = await createDocument('doklad', 'key-1').catch((error: unknown) => error)

    // The narrowing must not have thrown the carve-out out with the bathwater.
    expect(rejection).toBeInstanceOf(VersionConflictError)
  })
})
