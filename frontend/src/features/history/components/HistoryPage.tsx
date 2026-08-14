import { useCallback } from 'react'
import { listDocuments } from '../api/historyApi'
import { useHistoryList } from '../hooks/useHistoryList'
import { HistoryRows } from './HistoryRows'
import './HistoryPage.css'
import { HistoryRow } from './HistoryRow'

interface HistoryPageProps {
  // The wire's `document_type` (Cyrillic) travels with the id: the caller needs it to label the
  // editor's breadcrumb, and the row is the only place it is known. Translating it here would
  // put wire-vs-app vocabulary knowledge in a list component.
  onOpenDocument: (documentId: string, documentType: string) => void
  onBack: () => void
}

// ONE list, not two tabs. Story 18 removed the mode-select modal, so "a document made in manual
// mode" is no longer a category the user recognises — every finished generation becomes a
// Document via POST /documents/from-generation and lands in this same list. That left the second
// tab ("Генерации") showing the same work a second time under a different name, with rows that
// were not even clickable: the user's own runs, listed where opening one was impossible. A list
// whose rows do nothing is worse than no list, because the visitor spends a click finding out.
//
// `listGenerations` stays in the API module: it is the generations endpoint's client, covered by
// its own tests, and deleting a working binding because this screen stopped calling it would be
// throwing away the part that was never broken.
export function HistoryPage({ onOpenDocument, onBack }: HistoryPageProps) {
  // useCallback so the hook's effect does not see a new fetcher on every render.
  //
  // No explicit page size: `listDocuments` defaults to the server's own default (20), so passing
  // it here was a third copy of one number — restating a value this component has no opinion
  // about, in a place that would not be updated if the server's changed.
  const fetchPage = useCallback((cursor?: string) => listDocuments(undefined, cursor), [])
  const { items, isLoading, error, hasMore, loadMore } = useHistoryList(fetchPage)

  return (
    <div className="history-page" data-testid="history-page">
      <div className="history-head">
        <button type="button" className="history-back" data-testid="history-back" onClick={onBack}>
          ← Назад
        </button>
        <h1 className="history-title">Мои работы</h1>
      </div>

      <HistoryRows
        isLoading={isLoading}
        error={error}
        hasMore={hasMore}
        loadMore={loadMore}
        isEmpty={items.length === 0}
        emptyText="Вы ещё не создавали работ."
        testId="history-documents"
      >
        {items.map((d) => (
          <HistoryRow
            key={d.documentId}
            entry={d}
            formatDate={formatDate}
            onOpen={onOpenDocument}
          />
        ))}
      </HistoryRows>
    </div>
  )
}

// The wire sends UTC ISO; toLocaleDateString renders it in the reader's zone. An invalid or
// missing date renders as an em dash rather than "Invalid Date" — the row still says which
// document it is, which is the part that matters.
function formatDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
}
