import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { saveDocument } from '../documentApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// The 409 lost-update protocol, split out of documentApi.test.ts on the 200-line limit. It is a
// coherent concern of its own: every test here is about what happens AFTER the server refuses a
// stale version, which the request-shape tests next door say nothing about.
describe('documentApi save version conflict', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  // The 409 protocol, measured against the live backend 2026-07-17: a stale version with
  // different content returns {"error_code":"VERSION_CONFLICT"} and leaves the document
  // untouched. The backend prescribes the recovery ("Refetch and retry"), so saveDocument
  // performs it rather than pushing it onto callers.
  it('saveDocument refetches the current version and retries once after a 409', async () => {
    const fetchMock = vi
      .fn()
      // PUT with the caller's stale version -> conflict
      .mockResolvedValueOnce({
        ok: false,
        status: 409,
        json: async () => ({ error_code: 'VERSION_CONFLICT', message: 'conflict' }),
      })
      // GET -> the document is really at version 5
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          document_id: 'doc-1',
          status: 'draft',
          content: '<p>theirs</p>',
          version: 5,
        }),
      })
      // PUT replayed against 5 -> saved
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          document_id: 'doc-1',
          status: 'saved',
          content: '<p>ours</p>',
          version: 6,
        }),
      })
    vi.stubGlobal('fetch', fetchMock)

    const result = await saveDocument('doc-1', '<p>ours</p>', 1)

    expect(result).toEqual({ status: 'saved', version: 6, content: '<p>ours</p>' })
    expect(fetchMock).toHaveBeenCalledTimes(3)
    // The retry carries the REFETCHED version, not the caller's stale 1 — that is the whole
    // point, and asserting only the call count would pass on a retry that conflicts again.
    const [, retryInit] = fetchMock.mock.calls[2]
    expect(JSON.parse(retryInit.body)).toEqual({ content: '<p>ours</p>', version: 5 })
  })

  // Exactly one retry: a second conflict means the version we just fetched went stale within a
  // round trip, which looping cannot fix — it would only hammer the endpoint.
  it('saveDocument gives up after a second 409 rather than looping', async () => {
    const conflict = {
      ok: false,
      status: 409,
      json: async () => ({ error_code: 'VERSION_CONFLICT', message: 'conflict' }),
    }
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(conflict)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          document_id: 'doc-1',
          status: 'draft',
          content: '<p>theirs</p>',
          version: 5,
        }),
      })
      .mockResolvedValueOnce(conflict)
    vi.stubGlobal('fetch', fetchMock)

    await expect(saveDocument('doc-1', '<p>ours</p>', 1)).rejects.toThrow(
      'Документ был изменён другим сохранением.',
    )
    expect(fetchMock).toHaveBeenCalledTimes(3)
  })
})
