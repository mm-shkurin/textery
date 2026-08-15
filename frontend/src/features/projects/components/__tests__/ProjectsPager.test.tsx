import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ProjectsPager } from '../ProjectsPager'

// The pager derives everything it shows from `total`, and every way that arithmetic goes wrong is
// a page the user cannot reach or a button that walks them off the end of the result set. Rendered
// directly rather than through the page: the cases that matter are boundary values of `total` and
// `limit`, and driving them through a mocked feed would bury three numbers in a fixture.
describe('ProjectsPager', () => {
  function renderPager(props: Partial<Parameters<typeof ProjectsPager>[0]> = {}) {
    const onPage = vi.fn()
    render(<ProjectsPager page={1} limit={20} total={100} onPage={onPage} {...props} />)
    return onPage
  }

  // Not an empty <nav>: a control that can only ever be disabled is chrome the user has to read
  // and then ignore.
  it.each([
    ['there is nothing to page', 0],
    ['everything fits on one page', 20],
  ])('renders nothing when %s', (_name, total) => {
    renderPager({ total })
    expect(screen.queryByTestId('projects-pager')).toBeNull()
  })

  // The boundary the naive `total / limit` gets wrong: 21 items at 20 per page is two pages, and
  // a floor here would hide the last item from every user.
  it('counts a partial last page as a page', () => {
    renderPager({ total: 21 })
    expect(screen.getByTestId('projects-page-position')).toHaveTextContent('1 из 2')
  })

  it('reports the position within the filtered set', () => {
    renderPager({ page: 3, total: 100 })
    expect(screen.getByTestId('projects-page-position')).toHaveTextContent('3 из 5')
  })

  // Page 1 has no previous page and the last page has no next one. Asserted as disabled rather
  // than absent: a control that disappears at the ends makes the row jump under the pointer.
  it('disables the step that would leave the result set', () => {
    renderPager({ page: 1, total: 100 })
    expect(screen.getByTestId('projects-page-prev')).toBeDisabled()
    expect(screen.getByTestId('projects-page-next')).toBeEnabled()
  })

  it('disables the next step on the last page', () => {
    renderPager({ page: 5, total: 100 })
    expect(screen.getByTestId('projects-page-prev')).toBeEnabled()
    expect(screen.getByTestId('projects-page-next')).toBeDisabled()
  })

  // A page number past the end — reachable by hand-editing `?page=`, which is exactly what the URL
  // being the source of truth invites — must not offer a step further out.
  it('disables the next step on a page past the end', () => {
    renderPager({ page: 9, total: 100 })
    expect(screen.getByTestId('projects-page-next')).toBeDisabled()
  })

  it('asks for the adjacent page by number', () => {
    const onPage = renderPager({ page: 3, total: 100 })

    fireEvent.click(screen.getByTestId('projects-page-next'))
    expect(onPage).toHaveBeenCalledWith(4)

    fireEvent.click(screen.getByTestId('projects-page-prev'))
    expect(onPage).toHaveBeenCalledWith(2)
    expect(onPage).toHaveBeenCalledTimes(2)
  })

  // `limit: 0` is what an empty or malformed `limit` field on the wire deserialises to, and
  // dividing by it yields Infinity — a pager claiming infinitely many pages. The clamp is the
  // guard; this is what proves it is not decoration.
  it('survives a zero page size rather than claiming infinite pages', () => {
    renderPager({ limit: 0, total: 100 })
    expect(screen.getByTestId('projects-page-position')).toHaveTextContent('1 из 100')
  })

  // The pager is landmark navigation, so it is named. Reached by role here, the way assistive
  // technology reaches it, rather than by the testid every other case uses.
  it('is a named navigation landmark', () => {
    renderPager({ total: 100 })
    expect(screen.getByRole('navigation', { name: 'Страницы проектов' })).toBeInTheDocument()
  })
})
