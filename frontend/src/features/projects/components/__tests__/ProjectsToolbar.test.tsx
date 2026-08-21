import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ProjectsToolbar } from '../ProjectsToolbar'

// The toolbar is a controlled component: it owns no state and every interaction is a callback the
// page turns into a URL change. So what can go wrong here is a handler wired to the wrong prop, a
// value that does not round-trip, and the sort list drifting from the five orders the server's
// allowlist accepts — a label added here without a matching server value is a 400 the user cannot
// explain.
describe('ProjectsToolbar', () => {
  function renderToolbar(props: Partial<Parameters<typeof ProjectsToolbar>[0]> = {}) {
    const handlers = {
      onQueryChange: vi.fn(),
      onSortChange: vi.fn(),
      onViewChange: vi.fn(),
    }
    render(
      <ProjectsToolbar
        q=""
        sort="created_desc"
        view="grid"
        resultCount={null}
        {...handlers}
        {...props}
      />,
    )
    return handlers
  }

  it('shows the current query in the search box', () => {
    renderToolbar({ q: 'экономика' })
    expect(screen.getByTestId('projects-search')).toHaveValue('экономика')
  })

  it('reports each keystroke as the whole new query', () => {
    const { onQueryChange } = renderToolbar({ q: 'эконом' })

    fireEvent.change(screen.getByTestId('projects-search'), { target: { value: 'экономи' } })

    expect(onQueryChange).toHaveBeenCalledTimes(1)
    expect(onQueryChange).toHaveBeenCalledWith('экономи')
  })

  // Enter inside the search field must not reload the page — a real submit would throw away the
  // feed and land the user back on an unfiltered page 1.
  it('swallows the form submit rather than navigating', () => {
    renderToolbar({ q: 'a' })
    const form = screen.getByTestId('projects-search').closest('form')
    expect(form).toBeInstanceOf(HTMLFormElement)

    // `fireEvent.submit` returns false when a handler called preventDefault.
    expect(fireEvent.submit(form!)).toBe(false)
  })

  it('offers exactly the five orders the server accepts', () => {
    renderToolbar()
    const options = screen.getAllByRole('option').map((option) => ({
      value: option.getAttribute('value'),
      label: option.textContent,
    }))

    expect(options).toEqual([
      { value: 'created_desc', label: 'Сначала новые' },
      { value: 'created_asc', label: 'Сначала старые' },
      { value: 'updated_desc', label: 'По дате изменения' },
      { value: 'title_asc', label: 'По названию' },
      { value: 'type_asc', label: 'По типу' },
    ])
  })

  it('selects the current order and reports a change by its wire value', () => {
    const { onSortChange } = renderToolbar({ sort: 'title_asc' })
    const select = screen.getByTestId('projects-sort')
    expect(select).toHaveValue('title_asc')

    fireEvent.change(select, { target: { value: 'type_asc' } })

    expect(onSortChange).toHaveBeenCalledTimes(1)
    expect(onSortChange).toHaveBeenCalledWith('type_asc')
  })

  // The chosen view is announced through `aria-pressed`, and the stylesheet follows that same
  // attribute — so this assertion covers the a11y contract and the styling hook at once.
  it('announces the chosen view as pressed', () => {
    renderToolbar({ view: 'list' })
    expect(screen.getByTestId('projects-view-grid')).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByTestId('projects-view-list')).toHaveAttribute('aria-pressed', 'true')
  })

  it('reports a view choice', () => {
    const { onViewChange } = renderToolbar({ view: 'grid' })

    fireEvent.click(screen.getByTestId('projects-view-list'))

    expect(onViewChange).toHaveBeenCalledTimes(1)
    expect(onViewChange).toHaveBeenCalledWith('list')
  })

  // The count belongs to a search. On the unfiltered feed it would restate the number of cards the
  // user is already looking at, and `null` — not `0` — is how the page says "not searching".
  it('hides the result count when no search is active', () => {
    renderToolbar({ resultCount: null })
    expect(screen.queryByTestId('projects-result-count')).toBeNull()
  })

  // Zero is a result count, not the absence of one. The `!== null` test rather than a truthiness
  // one is what keeps «Найдено: 0» on screen for a search that matched nothing.
  it('reports a search that matched nothing', () => {
    renderToolbar({ q: 'ксчт', resultCount: 0 })
    expect(screen.getByTestId('projects-result-count')).toHaveTextContent('Найдено: 0')
  })

  it('reports the size of a non-empty result set', () => {
    renderToolbar({ q: 'э', resultCount: 42 })
    expect(screen.getByTestId('projects-result-count')).toHaveTextContent('Найдено: 42')
  })

  // Reached by role and name, the way assistive technology reaches them, rather than by the
  // testids the rest of this file uses: `<fieldset>` and `<input type="search">` carry these roles
  // natively, and an element swapped back to a plain `<div>` would keep every other assertion here
  // green.
  it('exposes the view toggle and the search field as named controls', () => {
    renderToolbar()
    expect(screen.getByRole('group', { name: 'Вид списка' })).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Поиск по проектам' })).toBeInTheDocument()
  })

  // The search landmark is asserted by ELEMENT, not by `getByRole('search')`, and that is a
  // limitation of the test stack rather than of the markup: the `aria-query` table bundled with
  // @testing-library/dom predates `<search>` and maps it to no role at all, so the role query finds
  // nothing while every current browser exposes the landmark. Pinned on the tag so a revert to a
  // plain `<div>` — which would drop the landmark for real — still turns this red.
  it('wraps the search field in a search landmark', () => {
    const { container } = render(
      <ProjectsToolbar
        q=""
        sort="created_desc"
        view="grid"
        resultCount={null}
        onQueryChange={vi.fn()}
        onSortChange={vi.fn()}
        onViewChange={vi.fn()}
      />,
    )
    const landmark = container.querySelector('search')
    expect(landmark).toBeInstanceOf(HTMLElement)
    expect(landmark!.querySelector('input[type="search"]')).toBeInstanceOf(HTMLInputElement)
  })
})
