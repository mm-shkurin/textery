import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createGeneration, getGeneration } from '../generationApi'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// Signing in is SETUP here, not subject: both endpoints now go through `authorizedRequest`, so
// without a session every call below fails before fetch is reached. The retry/refresh machinery
// that setup enables is pinned in auth/api/__tests__/authorizedRequest.test.ts — these tests
// cover what this module owns: the wire mapping and the error text.
describe('generationApi', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  it('createGeneration posts topic and returns generationId + status', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ generation_id: 'gen-1', status: 'pending' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await createGeneration('Квантовые компьютеры')

    expect(result).toEqual({ generationId: 'gen-1', status: 'pending' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/generations')
    expect(JSON.parse(init.body)).toMatchObject({
      topic: 'Квантовые компьютеры',
      document_type: 'doklad',
      volume_pages: 5,
    })
  })

  // The whole point of the session: the backend cannot associate a generation with a user it was
  // never told about. Without this assertion, dropping the header breaks nothing any other test
  // in this file would notice — every one of them passes against an anonymous request.
  it('createGeneration sends the access token', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ generation_id: 'gen-1', status: 'pending' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await createGeneration('Тема')

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer access-1')
  })

  it('getGeneration sends the access token', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ generation_id: 'gen-1', status: 'pending', content: null }),
    })
    vi.stubGlobal('fetch', fetchMock)

    await getGeneration('gen-1')

    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer access-1')
  })

  // Signing out mid-poll must not read as "your document failed" — the request was fine, the
  // user is not signed in. The typed error is what lets the UI tell those apart.
  it('rejects with SessionExpiredError when no session exists, without calling the API', async () => {
    clearSession()
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    await expect(createGeneration('Тема')).rejects.toBeInstanceOf(SessionExpiredError)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('createGeneration surfaces server error detail on non-OK response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Тема слишком короткая' }),
      }),
    )

    await expect(createGeneration('x')).rejects.toThrow('Тема слишком короткая')
  })

  it('createGeneration falls back to generic message when body has no detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('not json')
        },
      }),
    )

    await expect(createGeneration('x')).rejects.toThrow('HTTP 500')
  })

  it('getGeneration maps snake_case response to GenerationStatus', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          generation_id: 'gen-1',
          status: 'completed',
          content: '# Доклад',
          topic: 'Тема',
          volume_pages: 7,
          document_type: 'doklad',
          created_at: '2026-07-10T00:00:00Z',
        }),
      }),
    )

    const result = await getGeneration('gen-1')

    expect(result.volumePages).toBe(7)
    expect(result.content).toBe('# Доклад')
  })
})
