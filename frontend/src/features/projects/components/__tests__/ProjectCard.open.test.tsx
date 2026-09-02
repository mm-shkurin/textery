import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ProjectCard } from '../ProjectCard'
import { DOCUMENT, GENERATION, UNKNOWN_TYPE_PROJECT } from './projectFixtures'
import projectCardStyles from '../ProjectCard.module.css'

// Opening a card. Two rules decide whether the control exists at all — only a DOCUMENT has an
// editor behind it, and only a screen that wired `onOpen` can go there — and the third is that the
// control has to be a real one: the card is block content, so the tempting shape is a `<div>` with
// an onClick, which is unreachable by keyboard and announces nothing.
describe('ProjectCard open affordance', () => {
  it('opens a document by its title', () => {
    const onOpen = vi.fn()
    render(<ProjectCard project={DOCUMENT} onOpen={onOpen} />)

    // By ROLE and accessible name, not by testid: a `<div onClick>` satisfies a testid lookup and
    // this query is the thing it cannot satisfy.
    fireEvent.click(screen.getByRole('button', { name: DOCUMENT.title! }))

    expect(onOpen).toHaveBeenCalledTimes(1)
    expect(onOpen).toHaveBeenCalledWith(DOCUMENT)
  })

  // A generation is a record of work that never became a document, and its id comes from the other
  // table entirely — following it to the editor would open nothing, or worse, someone else's row.
  it('offers no way to open a generation', () => {
    render(<ProjectCard project={GENERATION} onOpen={vi.fn()} />)
    expect(screen.queryByRole('button', { name: GENERATION.title! })).toBeNull()
  })

  it('offers no way to open a card where the screen wired no handler', () => {
    render(<ProjectCard project={DOCUMENT} />)
    // Именно ОТКРЫТИЯ нет — карточка теперь всегда несёт «···» (действия story 11, пока
    // недоступные), поэтому «кнопок на карточке нет» больше не то же самое, что «открыть
    // нельзя». Проверяем отсутствие контрола с названием документа.
    expect(screen.queryByRole('button', { name: DOCUMENT.title! })).toBeNull()
    // The title is still shown — it is the card's content, not the control's label.
    expect(screen.getByTestId('project-card-title')).toHaveTextContent(DOCUMENT.title!)
  })

  // The class the stylesheet hangs `cursor: pointer` and the focus ring on. Pinned because it is
  // the one part of "this card is openable" that no behavioural assertion above would catch.
  it('marks an openable card for the stylesheet and leaves the others alone', () => {
    const { unmount } = render(<ProjectCard project={DOCUMENT} onOpen={vi.fn()} />)
    expect(screen.getByTestId('project-card')).toHaveClass(
      projectCardStyles['project-card-openable'],
    )
    unmount()

    render(<ProjectCard project={GENERATION} onOpen={vi.fn()} />)
    expect(screen.getByTestId('project-card')).not.toHaveClass(
      projectCardStyles['project-card-openable'],
    )
  })

  // A document with no title is labelled by the start of its own text: naming every untitled
  // доклад "Доклад" is what made them indistinguishable in «Мои работы» and therefore unopenable.
  it('labels an untitled document by its preview', () => {
    const untitled = { ...DOCUMENT, title: null, preview: 'Первые слова документа' }
    const onOpen = vi.fn()
    render(<ProjectCard project={untitled} onOpen={onOpen} />)

    fireEvent.click(screen.getByRole('button', { name: 'Первые слова документа' }))

    expect(onOpen).toHaveBeenCalledWith(untitled)
  })

  // With neither a title nor a preview the button would otherwise have no accessible name at all —
  // a control a screen-reader user is told is a button and nothing else. The type label is a poor
  // name and a far better one than none.
  it('falls back to the type label when a document has neither title nor preview', () => {
    const nameless = { ...DOCUMENT, title: null, preview: null }
    render(<ProjectCard project={nameless} onOpen={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Реферат' })).toBeInTheDocument()
  })

  // The label falls back to the app's own vocabulary, so a wire type this build has never heard of
  // still names the control something — the raw wire string, which is what the server sent.
  it('names the control for a document of an unknown type', () => {
    render(
      <ProjectCard
        project={{ ...UNKNOWN_TYPE_PROJECT, title: null, preview: null }}
        onOpen={vi.fn()}
      />,
    )

    expect(
      screen.getByRole('button', { name: UNKNOWN_TYPE_PROJECT.documentType }),
    ).toBeInTheDocument()
  })

  // Keyboard activation is asserted through the ELEMENT rather than by firing Enter and Space:
  // jsdom does not implement a button's default activation behaviour, so a keyDown here produces
  // no click and a test that fired one and then clicked anyway would be asserting nothing.
  //
  // What actually guarantees Enter and Space is that this is a real `<button>` — the previous shape
  // was a `<div role="button">` re-implementing both by hand, and a revert to it would keep every
  // click assertion above green while dropping keyboard access. The tag name and the absence of a
  // hand-set tabIndex are what tell the two apart.
  it('is a real button rather than a div wearing the role', () => {
    render(<ProjectCard project={DOCUMENT} onOpen={vi.fn()} />)
    const control = screen.getByRole('button', { name: DOCUMENT.title! })

    expect(control.tagName).toBe('BUTTON')
    // `type="button"` and not the HTML default `submit`: cards render inside the page, and a
    // submit button would post any form that ever wraps them.
    expect(control).toHaveAttribute('type', 'button')
    // Focusable by the platform, so no tabIndex is needed — and one set here would put the card
    // in a hand-managed tab order that has to be maintained against every neighbour.
    expect(control).not.toHaveAttribute('tabindex')
    expect(control).not.toHaveAttribute('role')
  })
})
