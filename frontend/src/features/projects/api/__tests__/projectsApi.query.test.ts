import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { listProjects } from '../projectsApi'
import { clearSession, saveSession } from '../../../../shared/session/authSession'
import { FEED_PATH, stubFetchJson } from './projectsWireFixtures'

// What `listProjects` puts on the URL, and — just as much the point — what it leaves off.
//
// `queryStringOf` is the module's only branching code, and every existing suite here calls
// `listProjects()` with no arguments, so all four `!== undefined` arms and the whitespace carve-out
// were unexecuted. The risk they carry is not a crash: a client that emitted `?page=1&limit=20` by
// default would be a SECOND place the contract's defaults live, free to drift from the server that
// owns them, and a client that sent `?q=%20%20` would make the feed run a content scan for nothing.
//
// Asserted on the whole URL string with `toBe`, never on a substring: `expect(url).toContain('q=')`
// passes on a URL that also carries three parameters the caller never named.
describe('listProjects query string', () => {
  beforeEach(() => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })
  })

  afterEach(() => {
    clearSession()
    vi.unstubAllGlobals()
  })

  const emptyPage = { items: [], total: 0, page: 1, limit: 20 }

  async function urlOf(params?: Parameters<typeof listProjects>[0]): Promise<string> {
    const fetchMock = stubFetchJson(emptyPage)
    await listProjects(params)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    return fetchMock.mock.calls[0][0] as string
  }

  it('sends the bare path when the caller names no parameters', async () => {
    expect(await urlOf()).toBe(FEED_PATH)
  })

  // An object with every key absent is not the same code path as no object at all — the first
  // reaches `new URLSearchParams()` and the four guards, the second returns early — and both have
  // to produce the same URL or the feed's first load would differ from its reload.
  it('sends the bare path when an object names no parameters', async () => {
    expect(await urlOf({})).toBe(`${FEED_PATH}`)
  })

  it('carries a search query', async () => {
    expect(await urlOf({ q: 'экономика' })).toBe(
      `${FEED_PATH}?q=%D1%8D%D0%BA%D0%BE%D0%BD%D0%BE%D0%BC%D0%B8%D0%BA%D0%B0`,
    )
  })

  // The empty box and the whitespace-only box are the same thing to the server, and neither is a
  // search. Sending `?q=` would put a parameter that means nothing into the browser history entry
  // the feed restores from.
  it.each([
    ['empty', ''],
    ['whitespace only', '   '],
    ['a tab', '\t'],
  ])('omits a %s query', async (_name, q) => {
    expect(await urlOf({ q })).toBe(FEED_PATH)
  })

  // Trimmed for the DECISION, sent untrimmed: the server owns what a query means, and a client
  // that silently rewrote 'машина ' to 'машина' would be answering a different question than the
  // one the user typed.
  it('sends a padded query as the user typed it', async () => {
    expect(await urlOf({ q: ' a ' })).toBe(`${FEED_PATH}?q=+a+`)
  })

  it('carries a sort order', async () => {
    expect(await urlOf({ sort: 'title_asc' })).toBe(`${FEED_PATH}?sort=title_asc`)
  })

  it('carries a page number', async () => {
    expect(await urlOf({ page: 3 })).toBe(`${FEED_PATH}?page=3`)
  })

  it('carries an explicit limit', async () => {
    expect(await urlOf({ limit: 50 })).toBe(`${FEED_PATH}?limit=50`)
  })

  // Page 1 and limit 20 are the SERVER's defaults, and the client states them only when the caller
  // does. This case exists because the tempting implementation — filling them in here — passes
  // every other test in this file.
  it('states page 1 only when the caller asked for it', async () => {
    expect(await urlOf({ page: 1 })).toBe(`${FEED_PATH}?page=1`)
    expect(await urlOf({ sort: 'created_desc' })).toBe(`${FEED_PATH}?sort=created_desc`)
  })

  // Order matters to nothing but readability of a failure, so it is pinned: a URL whose parameters
  // shuffle between builds turns every assertion in this file into a flake.
  it('orders the parameters q, sort, page, limit', async () => {
    expect(await urlOf({ limit: 5, page: 2, sort: 'type_asc', q: 'ab' })).toBe(
      `${FEED_PATH}?q=ab&sort=type_asc&page=2&limit=5`,
    )
  })
})
