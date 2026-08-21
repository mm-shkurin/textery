import { useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { ProjectPage } from '../api/projectsApi'
import type { FeedParams } from './feedQueryParams'

// The cache entry a feed page is stored under. Exported because the retry mutation writes to the
// exact page the user is looking at rather than asking for the whole list again.
export function projectsQueryKey(input: { q: string; sort: string; page: number }) {
  return ['projects', input.q, input.sort, input.page] as const
}

// The two writes the feed makes to the shared cache, kept apart from the read: one patches the
// row the user just acted on, the other asks for everything again.
export function useProjectsFeedCache(key: FeedParams) {
  const client = useQueryClient()
  const { q, sort, page } = key

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
        projectsQueryKey({ q, sort, page }),
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
    [client, q, sort, page],
  )

  // Marks every cached feed page stale, so the one on screen refetches and the rest do on their
  // next visit. Used by the error banner's «Повторить» — a deliberate user request for fresh data.
  const reload = useCallback(() => {
    void client.invalidateQueries({ queryKey: ['projects'] })
  }, [client])

  return { markRetried, reload }
}
