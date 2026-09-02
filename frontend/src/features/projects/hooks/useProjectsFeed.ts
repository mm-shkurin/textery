import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { listProjects, type ProjectSummary } from '../api/projectsApi'
import { describeLoadFailure } from '../api/loadFailureMessages'
import { mergeFeedParams, readFeedParams, type FeedParamsPatch } from '../utils/feedQueryParams'
import { projectsQueryKey, useProjectsFeedCache } from './useProjectsFeedCache'

export { projectsQueryKey }

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

// The typed box stays live while the request that answers it waits for the typist to pause.
function useDebouncedQuery(q: string): string {
  const [debouncedQ, setDebouncedQ] = useState(q)
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [q])
  return debouncedQ
}

/**
 * The feed's data and the URL that describes it.
 *
 * `q`, `sort` and `page` live in the query string (see feedQueryParams) rather than in component
 * state, so opening a project and coming back re-renders the same filtered feed.
 *
 * The data itself lives in the shared query cache, keyed by exactly those three values. That is
 * what makes the return trip instant: the same key resolves to the page already fetched, and a
 * refetch happens in the background only once the entry is stale. It also retires the sequence
 * guard this hook used to need — a response is written under the key it was requested for, so a
 * slow `q=A` landing after a fast `q=B` can no longer paint A's results under B's query.
 */
export function useProjectsFeed() {
  const [params, setParams] = useSearchParams()
  const { q, sort, page } = readFeedParams(params)
  const debouncedQ = useDebouncedQuery(q)

  const query = useQuery({
    queryKey: projectsQueryKey({ q: debouncedQ, sort, page }),
    queryFn: ({ signal }) => listProjects({ q: debouncedQ, sort, page, signal }),
    // Paging keeps the previous page on screen while the next one loads, instead of emptying the
    // grid and jumping the scroll position.
    placeholderData: keepPreviousData,
  })

  const update = useCallback(
    (next: FeedParamsPatch) => {
      setParams(mergeFeedParams(params, next), { replace: next.q !== undefined })
    },
    [params, setParams],
  )

  const { markRetried, reload } = useProjectsFeedCache({ q: debouncedQ, sort, page })

  return {
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    page: query.data?.page ?? page,
    limit: query.data?.limit ?? DEFAULT_LIMIT,
    loading: query.isPending,
    // `describeLoadFailure`, never `failure.message`: a 5xx arrives as a bare `HttpError`, which is
    // not an `Error`, so `.message` would paint "undefined" on the page. It also keeps the
    // expired-session sentence intact instead of retitling it as a feed failure.
    error: query.error ? describeLoadFailure(query.error) : null,
    q,
    sort,
    requestedPage: page,
    update,
    reload,
    markRetried,
  }
}
