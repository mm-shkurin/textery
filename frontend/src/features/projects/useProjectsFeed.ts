import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { listProjects, type ProjectSummary } from './api/projectsApi'
import { describeLoadFailure } from './api/loadFailureMessages'

// The server's own default page size. Mirrored here only so the pager can compute a page count
// before the first response arrives; every request still omits `limit` and lets the server decide.
export const DEFAULT_LIMIT = 20

// Long enough that a typist does not fire a request per keystroke, short enough that the feed
// still feels live. This is a UI affordance and NOT the endpoint's bound — the content scan is
// bounded server-side by the query-length cap and the statement deadline.
export const SEARCH_DEBOUNCE_MS = 300

export interface FeedState {
  items: ProjectSummary[]
  total: number
  page: number
  limit: number
  loading: boolean
  error: string | null
}

const EMPTY: FeedState = { items: [], total: 0, page: 1, limit: DEFAULT_LIMIT, loading: true, error: null }

/**
 * The feed's data and the URL that describes it.
 *
 * `q`, `sort` and `page` live in the query string rather than in component state, so opening a
 * project and coming back — or refreshing, or sharing the link — re-renders the same filtered
 * feed instead of an unfiltered page 1.
 *
 * Responses are applied only if they belong to the latest request. Without the sequence guard a
 * slow `q=A` landing after a fast `q=B` would paint A's results under B's query — the classic
 * search race, and the one this screen is most exposed to because it debounces.
 */
export function useProjectsFeed() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const sort = params.get('sort') ?? 'created_desc'
  const page = Number(params.get('page') ?? '1')

  const [state, setState] = useState<FeedState>(EMPTY)
  const [debouncedQ, setDebouncedQ] = useState(q)
  const [reloadToken, setReloadToken] = useState(0)
  const latestRequest = useRef(0)

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [q])

  useEffect(() => {
    const sequence = ++latestRequest.current
    setState((current) => ({ ...current, loading: true, error: null }))
    listProjects({ q: debouncedQ, sort, page })
      .then((feed) => {
        if (sequence !== latestRequest.current) return
        setState({ ...feed, loading: false, error: null })
      })
      .catch((failure: unknown) => {
        if (sequence !== latestRequest.current) return
        // `describeLoadFailure`, never `failure.message`: a 5xx arrives as a bare `HttpError`,
        // which is not an `Error`, so `.message` would paint "undefined" on the page. It also
        // keeps the expired-session sentence intact instead of retitling it as a feed failure.
        setState((current) => ({ ...current, loading: false, error: describeLoadFailure(failure) }))
      })
  }, [debouncedQ, sort, page, reloadToken])

  const update = useCallback(
    (next: { q?: string; sort?: string; page?: number }) => {
      const merged = new URLSearchParams(params)
      if (next.q !== undefined) {
        // An empty box is the absence of a search, not a search for "". Deleting the parameter
        // keeps the restored URL identical to the one a user who never searched would have.
        if (next.q === '') merged.delete('q')
        else merged.set('q', next.q)
      }
      if (next.sort !== undefined) merged.set('sort', next.sort)
      // Changing the query or the order returns to page 1. Keeping the number is the classic bug:
      // the user lands on an empty page 4 of a 3-page result and reads it as "nothing found".
      if (next.page !== undefined) merged.set('page', String(next.page))
      else if (next.q !== undefined || next.sort !== undefined) merged.delete('page')
      setParams(merged, { replace: next.q !== undefined })
    },
    [params, setParams],
  )

  const reload = useCallback(() => setReloadToken((token) => token + 1), [])

  return { ...state, q, sort, requestedPage: page, update, reload }
}
