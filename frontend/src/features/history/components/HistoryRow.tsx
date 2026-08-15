import { memo, useCallback } from 'react'
import { documentTypeLabelFromWire } from '../../../shared/copy/documentTypeCopy'
import type { DocumentSummary } from '../api/historyApi'

interface HistoryRowProps {
  entry: DocumentSummary
  formatDate: (iso: string) => string
  onOpen: (documentId: string, documentType: string) => void
}

// One row of «Мои работы».
//
// The prop is `entry`, not `document`: a prop named after a browser global shadows it inside
// the component, which is how a stray `document.querySelector` becomes a type error nobody can
// read. Extracted from the list's `.map` and memoized because it was the jury's remark: a row rendered
// inline is re-created on every parent render, so paging in twenty more documents repainted the
// twenty already on screen. Its props are a document, a formatter and a callback — all stable
// across renders — so a row now re-renders only when its own document changes.
function HistoryRowComponent({ entry, formatDate, onOpen }: HistoryRowProps) {
  // Bound here rather than as an inline arrow at the call site: an arrow in the parent's JSX is a
  // new function every render, which is exactly what defeats the memo above.
  const open = useCallback(
    () => onOpen(entry.documentId, entry.documentType),
    [entry.documentId, entry.documentType, onOpen],
  )

  return (
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
  )
}

export const HistoryRow = memo(HistoryRowComponent)
