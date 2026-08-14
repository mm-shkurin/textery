import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { listProjects, type ProjectPage, type ProjectSummary } from '../api/projectsApi'
import { describeLoadFailure } from '../api/loadFailureMessages'

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

// The cache entry a feed page is stored under. Exported because the retry mutation writes to the
// exact page the user is looking at rather than asking for the whole list again.
export function projectsQueryKey(input: { q: string; sort: string; page: number }) {
  return ['projects', input.q, input.sort, input.page] as const
}

/**
 * The feed's data and the URL that describes it.
 *
 * `q`, `sort` and `page` live in the query string rather than in component state, so opening a
 * project and coming back — or refreshing, or sharing the link — re-renders the same filtered
 * feed instead of an unfiltered page 1.
 *
 * The data itself lives in the shared query cache, keyed by exactly those three values. That is
 * what makes the return trip instant: the same key resolves to the page already fetched, and a
 * refetch happens in the background only once the entry is stale. It also retires the sequence
 * guard this hook used to need — a response is written under the key it was requested for, so a
 * slow `q=A` landing after a fast `q=B` can no longer paint A's results under B's query.
 */
export function useProjectsFeed() {
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const sort = params.get('sort') ?? 'created_desc'
  // A hand-typed `?page=abc` is not a page. Falling back to 1 keeps `page=NaN` off the wire.
  const requested = Number(params.get('page') ?? '1')
  const page = Number.isFinite(requested) && requested >= 1 ? Math.trunc(requested) : 1

  const [debouncedQ, setDebouncedQ] = useState(q)
  const client = useQueryClient()

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(q), SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [q])

  const query = useQuery({
    queryKey: projectsQueryKey({ q: debouncedQ, sort, page }),
    queryFn: ({ signal }) => listProjects({ q: debouncedQ, sort, page, signal }),
    // Paging keeps the previous page on screen while the next one loads, instead of emptying the
    // grid and jumping the scroll position.
    placeholderData: keepPreviousData,
  })

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

  // What «Повторить» does to the list, without asking the server for all of it again.
  //
  // The jury's remark was the counter this replaces: a retry bumped `reloadToken` and the whole
  // page was refetched, so one row's change cost a full round trip and a spinner over rows that
  // had not moved. The retried card is patched where it already sits — it is running again, and
  // it can no longer be retried — and the page is invalidated in the background, so the server's
  // own ordering and status arrive without the user watching a blank grid.
  const markRetried = useCallback(
    (generationId: string) => {
      client.setQueryData(
        projectsQueryKey({ q: debouncedQ, sort, page }),
        (current: ProjectPage | undefined) =>
          current === undefined
            ? current
            : {
                ...current,
                items: current.items.map((item) =>
                  item.kind === 'generation' && item.id === generationId
                    ? { ...item, status: 'pending', retryable: false }
                    : item,
                ),
              },
      )
      void client.invalidateQueries({ queryKey: ['projects'] })
    },
    [client, debouncedQ, sort, page],
  )

  // Marks every cached feed page stale, so the one on screen refetches and the rest do on their
  // next visit. Used by the error banner's «Повторить» — a deliberate user request for fresh data.
  const reload = useCallback(() => {
    void client.invalidateQueries({ queryKey: ['projects'] })
  }, [client])

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
