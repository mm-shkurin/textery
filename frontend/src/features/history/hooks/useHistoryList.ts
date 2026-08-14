import { useCallback } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'
import type { Page } from '../api/historyApi'
import { describeFailure } from '../../../shared/api/send'

interface HistoryList<T> {
  items: T[]
  isLoading: boolean
  error: string | null
  hasMore: boolean
  loadMore: () => void
}

// The paging state machine behind both history tabs. One copy, because "fetch a page, append,
// stop when the cursor is null" is identical for documents and generations — only the fetcher
// and the row differ.
//
// Pages live in the shared cache under `key`, which is what the jury's remark asked for: leaving
// the tab and coming back shows the pages already loaded instead of starting the list again from
// the first request. `useInfiniteQuery` also retires the two things this hook used to hand-roll —
// appending pages, and the stale-response guard that stopped a slow first page from being merged
// after a retry. A response is stored under the page it was requested for, so it cannot land in
// the wrong list.
//
// `hasMore` is derived from the CURSOR, never from `items.length === limit`. The backend's last
// page carries items AND a null cursor, so a length check would fire one pointless request on
// every list whose size divides evenly by the limit, and would keep «показать ещё» on screen
// after the list had visibly ended.
export function useHistoryList<T>(
  key: string,
  fetchPage: (cursor?: string) => Promise<Page<T>>,
): HistoryList<T> {
  const query = useInfiniteQuery({
    queryKey: ['history', key],
    queryFn: ({ pageParam }: { pageParam?: string }) => fetchPage(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last: Page<T>) => last.nextCursor ?? undefined,
  })

  const { fetchNextPage, hasNextPage, isFetchingNextPage } = query

  const loadMore = useCallback(() => {
    if (!hasNextPage || isFetchingNextPage) return
    void fetchNextPage()
  }, [fetchNextPage, hasNextPage, isFetchingNextPage])

  return {
    items: query.data?.pages.flatMap((page) => page.items) ?? [],
    isLoading: query.isPending || isFetchingNextPage,
    // `describeFailure`, not `err.message`: a 5xx from the list endpoints arrives as a bare
    // `HttpError` object, which would collapse to the generic string and throw away the status.
    error: query.error ? describeFailure(query.error, 'Не удалось загрузить список') : null,
    hasMore: hasNextPage,
    loadMore,
  }
}
