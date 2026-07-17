import { useCallback, useState } from 'react'
import { listDocuments, listGenerations } from '../api/historyApi'
import { useHistoryList } from '../hooks/useHistoryList'
import { HistoryRows } from './HistoryRows'
import { documentTypeLabelFromWire } from '../../../shared/documentTypes'
import { TabButton } from './HistoryTabButton'
import './HistoryPage.css'

type Tab = 'documents' | 'generations'

interface HistoryPageProps {
  // The wire's `document_type` (Cyrillic) travels with the id: the caller needs it to label the
  // editor's breadcrumb, and the row is the only place it is known. Translating it here would
  // put wire-vs-app vocabulary knowledge in a list component.
  onOpenDocument: (documentId: string, documentType: string) => void
  onBack: () => void
}

// Two tabs rather than one merged feed, and the reason is the contract, not taste: the two
// endpoints paginate on independent keyset cursors, so interleaving them by date would either
// mis-order rows at page boundaries or require reading both lists to the end before showing
// anything. A single feed needs one server-side endpoint; until then, two honest lists beat one
// list that lies about order.
export type { Tab }

export function HistoryPage({ onOpenDocument, onBack }: HistoryPageProps) {
  const [tab, setTab] = useState<Tab>('documents')

  return (
    <div className="history-page" data-testid="history-page">
      <div className="history-head">
        <button type="button" className="history-back" data-testid="history-back" onClick={onBack}>
          ← Назад
        </button>
        <h1 className="history-title">Мои работы</h1>
      </div>

      <div className="history-tabs" role="tablist" aria-label="Разделы истории">
        <TabButton id="documents" active={tab} onSelect={setTab} label="Мои документы" />
        <TabButton id="generations" active={tab} onSelect={setTab} label="Генерации" />
      </div>

      {/* Keyed so switching tabs remounts the list: the hook owns cursor + items, and carrying
          one tab's cursor into the other's fetcher would page the wrong list.

          The panel carries the tabpanel half of the pattern the tablist above promises. Declaring
          role="tab" without it announces a widget whose content has no stated relationship to the
          tabs — the reader is told "tab 1 of 2, selected" and then has to guess what it selected. */}
      <div
        role="tabpanel"
        id={`history-panel-${tab}`}
        aria-labelledby={`history-tab-${tab}`}
        tabIndex={0}
      >
        {tab === 'documents' ? (
          <DocumentsTab key="documents" onOpenDocument={onOpenDocument} />
        ) : (
          <GenerationsTab key="generations" />
        )}
      </div>
    </div>
  )
}

function DocumentsTab({
  onOpenDocument,
}: {
  onOpenDocument: (id: string, documentType: string) => void
}) {
  // useCallback so the hook's effect does not see a new fetcher on every render.
  //
  // No explicit page size: `listDocuments` defaults to the server's own default (20), so passing
  // it here was a third copy of one number — restating a value this component has no opinion
  // about, in a place that would not be updated if the server's changed.
  const fetchPage = useCallback((cursor?: string) => listDocuments(undefined, cursor), [])
  const { items, isLoading, error, hasMore, loadMore } = useHistoryList(fetchPage)

  return (
    <HistoryRows
      isLoading={isLoading}
      error={error}
      hasMore={hasMore}
      loadMore={loadMore}
      isEmpty={items.length === 0}
      emptyText="Вы ещё не создавали документов."
      testId="history-documents"
    >
      {items.map((d) => (
        <button
          type="button"
          key={d.documentId}
          className="history-row"
          data-testid="history-document-row"
          onClick={() => onOpenDocument(d.documentId, d.documentType)}
        >
          <span className="history-row-title">{documentTypeLabelFromWire(d.documentType)}</span>
          <span className="history-row-meta">{formatDate(d.updatedAt)}</span>
        </button>
      ))}
    </HistoryRows>
  )
}

// Rows are not clickable: opening a generation means the chat workspace, and this story owns the
// manual editor. Wiring it would be inventing a flow Story 5 never specified — the list is
// honest about what it can do rather than offering a dead click.
function GenerationsTab() {
  const fetchPage = useCallback((cursor?: string) => listGenerations(undefined, cursor), [])
  const { items, isLoading, error, hasMore, loadMore } = useHistoryList(fetchPage)

  return (
    <HistoryRows
      isLoading={isLoading}
      error={error}
      hasMore={hasMore}
      loadMore={loadMore}
      isEmpty={items.length === 0}
      emptyText="Вы ещё не запускали генераций."
      testId="history-generations"
    >
      {items.map((g) => (
        <div className="history-row" key={g.generationId} data-testid="history-generation-row">
          <span className="history-row-title">{g.topic}</span>
          <span className="history-row-meta">
            {g.status} · {formatDate(g.createdAt)}
          </span>
        </div>
      ))}
    </HistoryRows>
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
