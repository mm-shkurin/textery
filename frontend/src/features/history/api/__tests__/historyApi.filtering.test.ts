import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { deleteDocument, listDocuments } from '../historyApi'
import { clearSession, saveSession } from '../../../auth/utils/authSession'

// The half of `historyApi` the component tests cannot reach: they mock the whole module, so the
// query string the filter turns into — and the DELETE's method and path — were executed by
// nothing. Both are places where being wrong is silent: a dropped parameter narrows nothing and
// the screen simply shows more rows than the user asked for.
describe('historyApi — filtering and deletion', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  function stubFetch(body: unknown = { items: [], next_cursor: null }, status = 200) {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: status < 400,
      status,
      json: async () => body,
    })
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  function requested(fetchMock: ReturnType<typeof vi.fn>): URL {
    return new URL(fetchMock.mock.calls[0][0], 'http://test')
  }

  it('carries the search text as the contract names it', async () => {
    const fetchMock = stubFetch()

    await listDocuments(20, undefined, { query: 'квантовые' })

    expect(requested(fetchMock).searchParams.get('q')).toBe('квантовые')
  })

  it('trims the search text before it reaches the wire', async () => {
    const fetchMock = stubFetch()

    await listDocuments(20, undefined, { query: '  отчёт  ' })

    expect(requested(fetchMock).searchParams.get('q')).toBe('отчёт')
  })

  it('omits a blank search rather than sending an empty parameter', async () => {
    const fetchMock = stubFetch()

    await listDocuments(20, undefined, { query: '   ' })

    // `?q=` is a client that sent the parameter and named nothing. The server refuses that rather
    // than ignoring it, so an empty box would answer 400 instead of listing everything.
    expect(requested(fetchMock).searchParams.has('q')).toBe(false)
  })

  it('carries both ends of the date window', async () => {
    const fetchMock = stubFetch()

    await listDocuments(20, undefined, { createdFrom: '2026-07-01', createdTo: '2026-07-31' })

    const params = requested(fetchMock).searchParams
    expect(params.get('created_from')).toBe('2026-07-01')
    expect(params.get('created_to')).toBe('2026-07-31')
  })

  it('omits a cleared date input', async () => {
    const fetchMock = stubFetch()

    await listDocuments(20, undefined, { createdFrom: '', createdTo: '' })

    // A cleared `<input type="date">` reports ''. Forwarded, it is the same refused empty
    // parameter as a blank search.
    const params = requested(fetchMock).searchParams
    expect(params.has('created_from')).toBe(false)
    expect(params.has('created_to')).toBe(false)
  })

  it('keeps paging alongside the filter', async () => {
    const fetchMock = stubFetch()

    await listDocuments(5, 'anchor-1', { query: 'отчёт' })

    // The filter NARROWS a keyset page; it does not replace the pagination. Dropping the cursor
    // here would restart a filtered list from the top on every «показать ещё».
    const params = requested(fetchMock).searchParams
    expect(params.get('limit')).toBe('5')
    expect(params.get('cursor')).toBe('anchor-1')
    expect(params.get('q')).toBe('отчёт')
  })

  it('sends no filter parameters when none were given', async () => {
    const fetchMock = stubFetch()

    await listDocuments()

    const params = requested(fetchMock).searchParams
    expect([...params.keys()]).toEqual(['limit'])
  })

  it('deletes one document by id', async () => {
    const fetchMock = stubFetch(null, 204)

    await deleteDocument('doc-1')

    expect(requested(fetchMock).pathname).toBe('/api/v1/documents/doc-1')
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: 'DELETE' })
  })

  it('reports a refused delete rather than treating it as done', async () => {
    stubFetch({ error_code: 'NOT_FOUND', message: 'document not found' }, 404)

    // A 404 is not folded into success. The server refuses a second delete on purpose, and a
    // client reporting «удалено» for a row that was never there would hide a delete aimed at the
    // wrong id — the one mistake on this path the user cannot undo.
    await expect(deleteDocument('doc-1')).rejects.toBeTruthy()
  })
})
