import type { ProjectView } from '../useProjectView'

// The five orders the contract allows, with the labels this screen shows for them. A table, not
// a chain of conditions: the server refuses anything outside its allowlist, so a label added here
// without a matching server value is a 400 the user cannot explain.
const SORT_OPTIONS: ReadonlyArray<{ value: string; label: string }> = [
  { value: 'created_desc', label: 'Сначала новые' },
  { value: 'created_asc', label: 'Сначала старые' },
  { value: 'updated_desc', label: 'По дате изменения' },
  { value: 'title_asc', label: 'По названию' },
  { value: 'type_asc', label: 'По типу' },
]

interface ProjectsToolbarProps {
  q: string
  sort: string
  view: ProjectView
  resultCount: number | null
  onQueryChange: (q: string) => void
  onSortChange: (sort: string) => void
  onViewChange: (view: ProjectView) => void
}

export function ProjectsToolbar({
  q,
  sort,
  view,
  resultCount,
  onQueryChange,
  onSortChange,
  onViewChange,
}: ProjectsToolbarProps) {
  return (
    <div className="projects-toolbar" data-testid="projects-toolbar">
      {/* `<search>` rather than `role="search"` on the form: the element carries the same role
          natively, and a role attribute duplicating an element's own semantics is one more thing
          that can be typo'd into silence.
          The form inside it stays — that is what makes Enter a submit the browser understands,
          and `onSubmit` prevents the default, because a real submit would reload the page and
          throw away the feed. */}
      <search className="projects-search">
        <form onSubmit={(event) => event.preventDefault()}>
          <input
            type="search"
            className="projects-search-input"
            data-testid="projects-search"
            aria-label="Поиск по проектам"
            placeholder="Поиск"
            value={q}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </form>
      </search>

      {/* The count is rendered only while a search is active: on the unfiltered feed it would
          restate the number of cards the user is already looking at. */}
      {resultCount !== null && (
        <span className="projects-result-count" data-testid="projects-result-count">
          Найдено: {resultCount}
        </span>
      )}

      <label className="projects-sort">
        <span className="projects-sort-label">Сортировка</span>
        <select
          data-testid="projects-sort"
          value={sort}
          onChange={(event) => onSortChange(event.target.value)}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      {/* `<fieldset>` rather than `role="group"`: a set of related controls is exactly what the
          element means, and it carries the role natively. No `<legend>` — the group's name is the
          `aria-label`, and a visible legend here would repeat what the two buttons already say.
          `aria-pressed` rather than a disabled active button: the current view must stay
          focusable and announced as chosen, not removed from the tab order. */}
      <fieldset className="projects-view-toggle" aria-label="Вид списка">
        <button
          type="button"
          data-testid="projects-view-grid"
          aria-pressed={view === 'grid'}
          onClick={() => onViewChange('grid')}
        >
          Плитка
        </button>
        <button
          type="button"
          data-testid="projects-view-list"
          aria-pressed={view === 'list'}
          onClick={() => onViewChange('list')}
        >
          Список
        </button>
      </fieldset>
    </div>
  )
}
