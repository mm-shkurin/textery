import type { ProjectView } from '../hooks/useProjectView'
import { SearchIcon, GridIcon, ListIcon, FilterIcon, SortIcon } from './ProjectsIcons'
import projectsToolbarStyles from './ProjectsToolbar.module.css'
import controlStyles from './ProjectsToolbarControls.module.css'

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

// `<search>` rather than `role="search"` on the form: the element carries the same role
// natively, and a role attribute duplicating an element's own semantics is one more thing that
// can be typo'd into silence.
// The form inside it stays — that is what makes Enter a submit the browser understands, and
// `onSubmit` prevents the default, because a real submit would reload the page and throw away
// the feed.
export function ProjectsSearchField({
  q,
  onQueryChange,
}: {
  q: string
  onQueryChange: (q: string) => void
}) {
  return (
    <search className={projectsToolbarStyles['projects-search']}>
      <form
        className={projectsToolbarStyles['projects-search-field']}
        onSubmit={(event) => event.preventDefault()}
      >
        <SearchIcon className={projectsToolbarStyles['projects-search-icon']} />
        <input
          type="search"
          className={projectsToolbarStyles['projects-search-input']}
          data-testid="projects-search"
          aria-label="Поиск по проектам"
          placeholder="Поиск проектов..."
          value={q}
          onChange={(event) => onQueryChange(event.target.value)}
        />
      </form>
    </search>
  )
}

// The frame draws an icon-only button here and opens a sort SHEET behind it. The sheet has no
// spec, so what ships is a real <select> wearing that button: the element sits transparent on top
// of the glyph, keeping the five orders reachable by keyboard and by screen reader, while the
// button underneath is what the user sees. A div-and-popover would have to re-implement both.
export function ProjectsSortSelect({
  sort,
  onSortChange,
}: {
  sort: string
  onSortChange: (sort: string) => void
}) {
  return (
    <div className={controlStyles['projects-sort']}>
      <SortIcon className={controlStyles['projects-sort-glyph']} />
      <select
        className={controlStyles['projects-sort-select']}
        data-testid="projects-sort"
        aria-label="Сортировка"
        value={sort}
        onChange={(event) => onSortChange(event.target.value)}
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

// The filter button the frame draws beside it. There is nothing behind it yet: neither
// `GET /api/v1/generations` nor `GET /api/v1/documents` accepts a filter, so a working control
// would be a promise the API cannot keep. It ships DISABLED rather than dead — a button that
// swallows clicks in silence reads as a broken screen, one that is visibly unavailable reads as
// a feature that has not arrived. It leaves with the story that adds filtering to the contract.
export function ProjectsFilterButton() {
  return (
    <button
      type="button"
      className={controlStyles['projects-icon-button']}
      data-testid="projects-filter"
      aria-label="Фильтры"
      title="Фильтры появятся позже"
      disabled
    >
      <FilterIcon />
    </button>
  )
}

// `<fieldset>` rather than `role="group"`: a set of related controls is exactly what the element
// means, and it carries the role natively. No `<legend>` — the group's name is the `aria-label`,
// and a visible legend here would repeat what the two buttons already say.
// `aria-pressed` rather than a disabled active button: the current view must stay focusable and
// announced as chosen, not removed from the tab order.
// The labels went from text to icons to match the design, so each button keeps an `aria-label`:
// an icon-only control with no name announces as "button" and nothing else.
// Hidden below the mobile breakpoint by CSS rather than removed here — the Figma mobile frames
// have no toggle at all (the note on the board reads «в мобильной версии только сеткой вид
// карточек»), and dropping it from the markup would also drop the stored preference of a user
// who resizes back.
export function ProjectsViewToggle({
  view,
  onViewChange,
}: {
  view: ProjectView
  onViewChange: (view: ProjectView) => void
}) {
  return (
    <fieldset className={projectsToolbarStyles['projects-view-toggle']} aria-label="Вид списка">
      <button
        type="button"
        data-testid="projects-view-grid"
        aria-label="Сеткой"
        aria-pressed={view === 'grid'}
        onClick={() => onViewChange('grid')}
      >
        <GridIcon className={projectsToolbarStyles['projects-view-icon']} />
      </button>
      <button
        type="button"
        data-testid="projects-view-list"
        aria-label="Списком"
        aria-pressed={view === 'list'}
        onClick={() => onViewChange('list')}
      >
        <ListIcon className={projectsToolbarStyles['projects-view-icon']} />
      </button>
    </fieldset>
  )
}
