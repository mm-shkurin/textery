import type { ReactNode } from 'react'

interface HistoryRowsProps {
  isLoading: boolean
  error: string | null
  hasMore: boolean
  loadMore: () => void
  isEmpty: boolean
  emptyText: string
  testId: string
  children: ReactNode
}

// The four states every paginated list has, in one place so both tabs answer them the same way.
// Extracted because getting "empty" wrong is easy and silent: an empty list and a list that
// failed to load look identical if you only render `items`.
export function HistoryRows({
  isLoading,
  error,
  hasMore,
  loadMore,
  isEmpty,
  emptyText,
  testId,
  children,
}: HistoryRowsProps) {
  // Error wins over empty: a failed fetch leaves items empty, and telling the visitor "you have
  // no documents" when the truth is "we could not ask" is a lie they would act on by creating a
  // duplicate.
  if (error) {
    return (
      <div className="history-error" role="alert" data-testid={`${testId}-error`}>
        {error}
      </div>
    )
  }

  // Only on the FIRST load: while paging, `items` are on screen and replacing them with a
  // spinner would throw away what the visitor is reading.
  if (isLoading && isEmpty) {
    return (
      <div className="history-loading" data-testid={`${testId}-loading`}>
        Загрузка…
      </div>
    )
  }

  if (isEmpty) {
    return (
      <div className="history-empty" data-testid={`${testId}-empty`}>
        {emptyText}
      </div>
    )
  }

  return (
    <div className="history-list" data-testid={testId}>
      {children}
      {hasMore && (
        <button
          type="button"
          className="history-more"
          data-testid={`${testId}-more`}
          onClick={loadMore}
          disabled={isLoading}
        >
          {isLoading ? 'Загрузка…' : 'Показать ещё'}
        </button>
      )}
    </div>
  )
}
