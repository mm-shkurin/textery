import type { HistoryFilter } from '../api/historyApi'
import './HistoryToolbar.css'

interface HistoryToolbarProps {
  filter: HistoryFilter
  onChange: (filter: HistoryFilter) => void
  // Rendered only while the list is actually narrowed: on the unfiltered history it would restate
  // the number of rows the user is already looking at.
  resultCount: number | null
}

const QUERY_LABEL_ID = 'history-search-label'

/**
 * «Поиск по истории» and «фильтровать по дате создания», in one row above the list.
 *
 * The three controls write into ONE filter object rather than three pieces of state: they are
 * applied together on the server, in one request, and splitting them here is what lets a screen
 * fire a search that has not yet picked up a date the user already chose.
 */
export function HistoryToolbar({ filter, onChange, resultCount }: HistoryToolbarProps) {
  const set = (patch: Partial<HistoryFilter>) => onChange({ ...filter, ...patch })
  const isFiltered = Boolean(filter.query?.trim() || filter.createdFrom || filter.createdTo)

  return (
    <div className="history-toolbar" data-testid="history-toolbar">
      {/* `<search>` carries the role natively — see ProjectsToolbar for why a duplicated
          `role="search"` is one more thing that can be typo'd into silence. The form makes Enter
          a submit the browser understands, and the default is prevented because a real submit
          would reload the page and throw the loaded pages away. */}
      <search className="history-search">
        <form className="history-search-field" onSubmit={(event) => event.preventDefault()}>
          <span id={QUERY_LABEL_ID} className="history-toolbar-label">
            Поиск
          </span>
          <input
            type="search"
            className="history-toolbar-input"
            data-testid="history-search"
            aria-labelledby={QUERY_LABEL_ID}
            placeholder="Название или текст работы"
            value={filter.query ?? ''}
            onChange={(event) => set({ query: event.target.value })}
          />
        </form>
      </search>

      <div className="history-dates">
        <label className="history-date-field">
          <span className="history-toolbar-label">С</span>
          <input
            type="date"
            className="history-toolbar-input"
            data-testid="history-created-from"
            value={filter.createdFrom ?? ''}
            onChange={(event) => set({ createdFrom: event.target.value })}
          />
        </label>
        <label className="history-date-field">
          <span className="history-toolbar-label">По</span>
          <input
            type="date"
            className="history-toolbar-input"
            data-testid="history-created-to"
            value={filter.createdTo ?? ''}
            onChange={(event) => set({ createdTo: event.target.value })}
          />
        </label>
      </div>

      {/* One reset for all three. Clearing a search box by hand leaves the dates in place, and a
          user who sees an empty list with an empty search box has no way to tell that a date
          window is still narrowing it. */}
      {isFiltered && (
        <button
          type="button"
          className="history-toolbar-reset"
          data-testid="history-filter-reset"
          onClick={() => onChange({})}
        >
          Сбросить
        </button>
      )}

      {resultCount !== null && (
        <span className="history-result-count" data-testid="history-result-count">
          Найдено: {resultCount}
        </span>
      )}
    </div>
  )
}
