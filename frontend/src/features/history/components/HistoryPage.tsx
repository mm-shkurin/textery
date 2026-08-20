import { useCallback, useState } from 'react'
import { listDocuments, type HistoryFilter } from '../api/historyApi'
import { useHistoryList } from '../hooks/useHistoryList'
import { useDeleteDocument } from '../hooks/useDeleteDocument'
import { HistoryRows } from './HistoryRows'
import styles from './HistoryPage.module.css'
import { HistoryRow } from './HistoryRow'
import { HistoryToolbar } from './HistoryToolbar'
import { HistoryDeleteModal } from './HistoryDeleteModal'
import { QueryBoundary } from '../../../shared/query/QueryBoundary'

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
function HistoryPageScreen({ onOpenDocument, onBack }: HistoryPageProps) {
  // useCallback so the hook's effect does not see a new fetcher on every render.
  //
  // No explicit page size: `listDocuments` defaults to the server's own default (20), so passing
  // it here was a third copy of one number — restating a value this component has no opinion
  // about, in a place that would not be updated if the server's changed.
  const [filter, setFilter] = useState<HistoryFilter>({})
  const fetchPage = useCallback(
    (cursor?: string) => listDocuments(undefined, cursor, filter),
    [filter],
  )
  // The filter is part of the CACHE KEY, not only of the request. Under one key the pages fetched
  // for «отчёт» would be appended to the pages fetched for the unfiltered list, and going back to
  // an earlier search would show whatever the last search left behind.
  const listKey = `documents:${filter.query ?? ''}:${filter.createdFrom ?? ''}:${filter.createdTo ?? ''}`
  const { items, isLoading, error, hasMore, loadMore } = useHistoryList(listKey, fetchPage)
  const deletion = useDeleteDocument()

  const isFiltered = Boolean(filter.query?.trim() || filter.createdFrom || filter.createdTo)

  return (
    <div className={styles['history-page']} data-testid="history-page">
      <div className={styles['history-head']}>
        <button
          type="button"
          className={styles['history-back']}
          data-testid="history-back"
          onClick={onBack}
        >
          ← Назад
        </button>
        <h1 className={styles['history-title']}>Мои работы</h1>
      </div>

      <HistoryToolbar
        filter={filter}
        onChange={setFilter}
        // Only while a filter is active, and only once loading has finished: a count rendered
        // mid-fetch reports the previous filter's rows against the new filter's label.
        resultCount={isFiltered && !isLoading ? items.length : null}
      />

      <HistoryRows
        isLoading={isLoading}
        error={error}
        hasMore={hasMore}
        loadMore={loadMore}
        isEmpty={items.length === 0}
        // The empty state has to say WHICH emptiness it is. «Вы ещё не создавали работ» under an
        // active search tells a user with fifty documents that they have none.
        emptyText={
          isFiltered ? 'Ничего не найдено по этому запросу.' : 'Вы ещё не создавали работ.'
        }
        testId="history-documents"
      >
        {items.map((d) => (
          <HistoryRow
            key={d.documentId}
            entry={d}
            formatDate={formatDate}
            onOpen={onOpenDocument}
            onDelete={deletion.request}
            isDeleting={deletion.isDeleting && deletion.pending?.documentId === d.documentId}
          />
        ))}
      </HistoryRows>

      {deletion.pending !== null && (
        <HistoryDeleteModal
          entry={deletion.pending}
          isDeleting={deletion.isDeleting}
          error={deletion.error}
          onCancel={deletion.cancel}
          onConfirm={deletion.confirm}
        />
      )}
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

/**
 * The screen, with the data cache it reads through.
 *
 * Wrapped here rather than only at the app root so the page can be rendered on its own — by a
 * test, by a future route — without silently requiring an ancestor it never names. The boundary
 * carries the same client either way, so nesting changes nothing at runtime.
 */
export function HistoryPage(props: Parameters<typeof HistoryPageScreen>[0]) {
  return (
    <QueryBoundary>
      <HistoryPageScreen {...props} />
    </QueryBoundary>
  )
}
