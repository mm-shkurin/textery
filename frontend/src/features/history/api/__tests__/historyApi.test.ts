import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { listDocuments, listGenerations } from '../historyApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// historyApi was the one API client with no test of its own: every HistoryPage test mocks the
// whole module (`vi.mock('../../api/historyApi')`), so the part that can actually be wrong —
// the snake_case wire → camelCase app mapping, and the query string that carries limit/cursor —
// was executed by nothing. A renamed or dropped field would have shipped green.
//
// These tests pin the two facts the component layer cannot: what goes out on the URL, and what
// comes back after mapping. `nextCursor` is asserted explicitly because null is the END marker
// (the last page carries items AND a null cursor), so collapsing it to undefined would make
// paging stop one page early or never stop at all.
describe('historyApi', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubFetchJson(body: unknown): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => body,
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  function requestedUrl(fetchMock: ReturnType<typeof vi.fn>): string {
    return fetchMock.mock.calls[0][0]
  }

  const DOCUMENT_WIRE = {
    document_id: 'doc-1',
    document_type: 'doklad',
    status: 'draft',
    version: 3,
    created_at: '2026-07-17T10:00:00Z',
    updated_at: '2026-07-17T11:00:00Z',
  }

  const GENERATION_WIRE = {
    generation_id: 'gen-1',
    status: 'completed',
    topic: 'Квантовые вычисления',
    document_type: 'referat',
    volume_pages: 12,
    created_at: '2026-07-17T09:00:00Z',
  }

  it('maps every document wire field onto its camelCase counterpart', async () => {
    stubFetchJson({ items: [DOCUMENT_WIRE], next_cursor: 'cursor-2' })

    const page = await listDocuments()

    expect(page).toEqual({
      items: [
        {
          documentId: 'doc-1',
          documentType: 'doklad',
          status: 'draft',
          version: 3,
          createdAt: '2026-07-17T10:00:00Z',
          updatedAt: '2026-07-17T11:00:00Z',
        },
      ],
      nextCursor: 'cursor-2',
    })
  })

  it('maps every generation wire field onto its camelCase counterpart', async () => {
    stubFetchJson({ items: [GENERATION_WIRE], next_cursor: null })

    const page = await listGenerations()

    expect(page).toEqual({
      items: [
        {
          generationId: 'gen-1',
          status: 'completed',
          topic: 'Квантовые вычисления',
          documentType: 'referat',
          volumePages: 12,
          createdAt: '2026-07-17T09:00:00Z',
        },
      ],
      nextCursor: null,
    })
  })

  // The end-of-list signal, asserted as its own case: a last page carries items AND a null
  // cursor, so `nextCursor` must survive as null rather than becoming undefined.
  it('preserves a null next_cursor as the end-of-list marker alongside items', async () => {
    stubFetchJson({ items: [DOCUMENT_WIRE], next_cursor: null })

    const page = await listDocuments()

    expect(page.items).toHaveLength(1)
    expect(page.nextCursor).toBeNull()
  })

  it('defaults to the server page size and sends no cursor on the first page', async () => {
    const fetchMock = stubFetchJson({ items: [], next_cursor: null })

    await listDocuments()

    expect(requestedUrl(fetchMock)).toBe('/api/v1/documents?limit=20')
  })

  it('sends the explicit limit and cursor when paging further', async () => {
    const fetchMock = stubFetchJson({ items: [], next_cursor: null })

    await listGenerations(5, 'opaque|cursor')

    expect(requestedUrl(fetchMock)).toBe('/api/v1/generations?limit=5&cursor=opaque%7Ccursor')
  })

  // An empty page is not an error and not the shape of a failure: it must map to an empty array,
  // never to undefined, or the list renderer crashes on `.map`.
  it('maps an empty page to an empty item list', async () => {
    stubFetchJson({ items: [], next_cursor: null })

    const page = await listGenerations()

    expect(page.items).toEqual([])
    expect(page.nextCursor).toBeNull()
  })

  // The refusal path: a non-ok response must surface the server's own message, not a bare
  // status, so the "Мои работы" screen can say what went wrong.
  it('surfaces the server message when the list request is refused', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        headers: { get: () => null },
        json: async () => ({ error_code: 'INVALID_CURSOR', message: 'Курсор недействителен' }),
      }),
    )

    await expect(listDocuments(20, 'garbage')).rejects.toThrow('Курсор недействителен')
  })
})
