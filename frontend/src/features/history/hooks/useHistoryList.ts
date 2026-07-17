import { useCallback, useEffect, useRef, useState } from 'react'
import type { Page } from '../../generation/api/historyApi'

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
// `hasMore` is derived from the CURSOR, never from `items.length === limit`. The backend's last
// page carries items AND a null cursor, so a length check would fire one pointless request on
// every list whose size divides evenly by the limit, and would keep "показать ещё" on screen
// after the list had visibly ended.
export function useHistoryList<T>(
  fetchPage: (cursor?: string) => Promise<Page<T>>,
): HistoryList<T> {
  const [items, setItems] = useState<T[]>([])
  const [cursor, setCursor] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [started, setStarted] = useState(false)

  // Guards the append against a stale response. Switching tabs remounts this hook, but
  // "показать ещё" clicked twice, or a slow first page landing after a retry, would otherwise
  // append the same rows twice. The ref is bumped per load; a response whose id no longer
  // matches is dropped rather than merged.
  const loadId = useRef(0)

  const load = useCallback(
    (nextCursor?: string) => {
      const id = ++loadId.current
      setIsLoading(true)
      setError(null)
      fetchPage(nextCursor)
        .then((page) => {
          if (id !== loadId.current) return
          // Append on paging, replace on the first load. `nextCursor` being undefined is what
          // distinguishes them — not items.length, which is 0 for both an empty list and a
          // fresh mount.
          setItems((prev) => (nextCursor ? [...prev, ...page.items] : page.items))
          setCursor(page.nextCursor)
          setIsLoading(false)
        })
        .catch((err: unknown) => {
          if (id !== loadId.current) return
          setError(err instanceof Error ? err.message : 'Не удалось загрузить список')
          setIsLoading(false)
        })
    },
    [fetchPage],
  )

  useEffect(() => {
    if (started) return
    setStarted(true)
    load()
  }, [load, started])

  const loadMore = useCallback(() => {
    if (!cursor || isLoading) return
    load(cursor)
  }, [cursor, isLoading, load])

  return { items, isLoading, error, hasMore: cursor !== null, loadMore }
}
