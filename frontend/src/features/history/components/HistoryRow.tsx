import { memo, useCallback } from 'react'
import { documentTypeLabelFromWire } from '../../../shared/copy/documentTypeCopy'
import type { DocumentSummary } from '../api/historyApi'

interface HistoryRowProps {
  entry: DocumentSummary
  formatDate: (iso: string) => string
  onOpen: (documentId: string, documentType: string) => void
  // Absent when the list is read-only. Optional rather than always-present so a future screen
  // that lists documents without owning them cannot accidentally render a delete it cannot honour.
  onDelete?: (entry: DocumentSummary) => void
  isDeleting?: boolean
}

// One row of «Мои работы».
//
// The prop is `entry`, not `document`: a prop named after a browser global shadows it inside
// the component, which is how a stray `document.querySelector` becomes a type error nobody can
// read. Extracted from the list's `.map` and memoized because it was the jury's remark: a row rendered
// inline is re-created on every parent render, so paging in twenty more documents repainted the
// twenty already on screen. Its props are a document, a formatter and a callback — all stable
// across renders — so a row now re-renders only when its own document changes.
function HistoryRowComponent({
  entry,
  formatDate,
  onOpen,
  onDelete,
  isDeleting = false,
}: HistoryRowProps) {
  // Bound here rather than as an inline arrow at the call site: an arrow in the parent's JSX is a
  // new function every render, which is exactly what defeats the memo above.
  const open = useCallback(
    () => onOpen(entry.documentId, entry.documentType),
    [entry.documentId, entry.documentType, onOpen],
  )

  const remove = useCallback(() => onDelete?.(entry), [entry, onDelete])

  // A wrapper, not a `<button>` containing a `<button>`: nested interactive elements are invalid
  // HTML, and browsers recover from them by dropping the inner control — so the delete would have
  // been unclickable in exactly the way that is hardest to notice from a jsdom test.
  return (
    <div className="history-row-wrap">
      <button
        type="button"
        className="history-row"
        data-testid="history-document-row"
        onClick={open}
      >
        {/* The title is what identifies the row, and its absence is what made reopening a document
          impossible: every row read "Доклад" and the user could not tell three reports apart.
          Falls back to the type label for a manual document created before titles existed — a
          blank row is a worse regression than a repeated one. */}
        <span className="history-row-title">
          {entry.title?.trim() || documentTypeLabelFromWire(entry.documentType)}
        </span>
        <span className="history-row-meta">
          {documentTypeLabelFromWire(entry.documentType)} · {formatDate(entry.updatedAt)}
        </span>
      </button>
      {onDelete !== undefined && (
        // The accessible name carries the document's own title. Twenty rows of «Удалить» are
        // twenty identically-named buttons to anyone listing the page's controls, and this is the
        // one action here that cannot be undone.
        <button
          type="button"
          className="history-row-delete"
          data-testid="history-document-delete"
          aria-label={`Удалить «${entry.title?.trim() || documentTypeLabelFromWire(entry.documentType)}»`}
          // aria-disabled, not the native attribute: a natively disabled button dispatches no
          // click at all, so a second press during the request would be swallowed silently
          // instead of reaching the handler's own in-flight guard.
          aria-disabled={isDeleting}
          onClick={remove}
        >
          ✕
        </button>
      )}
    </div>
  )
}

export const HistoryRow = memo(HistoryRowComponent)
