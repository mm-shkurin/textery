import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { ProjectCard } from '../ProjectCard'
import { DOCUMENT, GENERATION } from './projectFixtures'

// The «Повторить» affordance on a failed generation — the one control on this screen that costs
// money. Every case here is about when the button is OFFERED rather than about what it looks like:
// offering it on a row the server did not mark retryable is fail-open on a paid operation.
describe('ProjectCard retry affordance', () => {
  it('offers the retry only when the server marked the row retryable', () => {
    render(<ProjectCard project={GENERATION} onRetry={vi.fn()} />)
    expect(screen.getByTestId('project-card-retry')).toHaveTextContent('Повторить')
  })

  // `retryable` is read as the server sent it and never re-derived from `status`. A client
  // computing it from an enum it may not fully know would offer the button on a status it does not
  // recognise — which is why the fixture below is a `status: 'draft'` document, not a doctored
  // generation.
  it('offers no retry on a row the server did not mark retryable', () => {
    render(<ProjectCard project={DOCUMENT} onRetry={vi.fn()} />)
    expect(screen.queryByTestId('project-card-retry')).toBeNull()
  })

  // «Недавние проекты» shows the same rows the full list below it does, and only the full list
  // wires `onRetry`. A card rendered without the handler must not draw a button that does nothing.
  it('offers no retry where the screen wired no handler', () => {
    render(<ProjectCard project={GENERATION} />)
    expect(screen.queryByTestId('project-card-retry')).toBeNull()
  })

  it('asks to retry the generation by id', () => {
    const onRetry = vi.fn()
    render(<ProjectCard project={GENERATION} onRetry={onRetry} />)

    fireEvent.click(screen.getByTestId('project-card-retry'))

    expect(onRetry).toHaveBeenCalledTimes(1)
    // `undefined` for the overrides, explicitly asserted rather than left off: both pickers beside
    // this button default to «то же самое», and a plain repeat must forward NO override at all.
    // An empty object here instead would still be a body on the wire, and `{text_style: ""}` is a
    // value the server refuses — so the difference between the two is a broken button.
    expect(onRetry).toHaveBeenCalledWith(GENERATION.id, undefined)
  })

  it('asks to regenerate in the register the user picked', () => {
    const onRetry = vi.fn()
    render(<ProjectCard project={GENERATION} onRetry={onRetry} />)

    fireEvent.change(screen.getByTestId('project-card-retry-style'), {
      target: { value: 'художественный' },
    })
    fireEvent.click(screen.getByTestId('project-card-retry'))

    expect(onRetry).toHaveBeenCalledWith(GENERATION.id, { textStyle: 'художественный' })
  })

  it('asks to regenerate at the length the user picked', () => {
    const onRetry = vi.fn()
    render(<ProjectCard project={GENERATION} onRetry={onRetry} />)

    fireEvent.change(screen.getByTestId('project-card-retry-volume'), { target: { value: '8' } })
    fireEvent.click(screen.getByTestId('project-card-retry'))

    // A number, not the select's string: the wire field is an integer, and a string reaching the
    // server is a 422 the user cannot act on from a card.
    expect(onRetry).toHaveBeenCalledWith(GENERATION.id, { volumePages: 8 })
  })

  it('carries both choices when the user makes both', () => {
    const onRetry = vi.fn()
    render(<ProjectCard project={GENERATION} onRetry={onRetry} />)

    fireEvent.change(screen.getByTestId('project-card-retry-style'), {
      target: { value: 'научный' },
    })
    fireEvent.change(screen.getByTestId('project-card-retry-volume'), { target: { value: '2' } })
    fireEvent.click(screen.getByTestId('project-card-retry'))

    expect(onRetry).toHaveBeenCalledWith(GENERATION.id, {
      textStyle: 'научный',
      volumePages: 2,
    })
  })

  it('leaves the length alone when only the register was picked', () => {
    const onRetry = vi.fn()
    render(<ProjectCard project={GENERATION} onRetry={onRetry} />)

    fireEvent.change(screen.getByTestId('project-card-retry-style'), {
      target: { value: 'научный' },
    })
    fireEvent.click(screen.getByTestId('project-card-retry'))

    // The absent key is the point: present-and-undefined would still be a key the API client has
    // to know to skip, and «изменить объём» must not fire because the register changed.
    expect(onRetry.mock.calls[0][1]).not.toHaveProperty('volumePages')
  })

  it('offers only lengths the server accepts', () => {
    render(<ProjectCard project={GENERATION} onRetry={vi.fn()} />)

    const offered = Array.from(
      screen.getByTestId('project-card-retry-volume').querySelectorAll('option'),
    ).map((option) => option.getAttribute('value'))

    // Enumerated from the shared bounds, so the picker cannot produce a length the domain refuses.
    // '' is the «тот же объём» placeholder and sends nothing.
    expect(offered).toEqual(['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10'])
  })

  // The guard against a double-click lives in the hook; a button that stays live through the wait
  // invites one anyway.
  it('disables itself and says so while its own request is in flight', () => {
    render(<ProjectCard project={GENERATION} onRetry={vi.fn()} retrying />)
    const button = screen.getByTestId('project-card-retry')

    expect(button).toBeDisabled()
    expect(button).toHaveTextContent('Повторяем…')
  })

  // Announced, not merely rendered: the retry fails without moving anything else on the page, so a
  // user who does not happen to be looking at that card learns nothing otherwise.
  it('announces a retry failure on the card that failed', () => {
    render(<ProjectCard project={GENERATION} onRetry={vi.fn()} retryError="Не удалось повторить" />)
    const banner = screen.getByRole('alert')

    expect(banner).toHaveTextContent('Не удалось повторить')
    expect(banner).toHaveAttribute('data-testid', 'project-card-retry-error')
  })

  it('shows no failure banner before anything has failed', () => {
    render(<ProjectCard project={GENERATION} onRetry={vi.fn()} />)
    expect(screen.queryByRole('alert')).toBeNull()
  })

  // Every testid on the card takes the prefix, so «Недавние проекты» and the list below it can
  // show the same row without two elements answering to one identity lookup. Asserted on the retry
  // pair specifically — they were added after the prefix convention and are the ones most likely
  // to have missed it.
  it('namespaces the retry controls when the section asks for a prefix', () => {
    render(
      <ProjectCard
        project={GENERATION}
        onRetry={vi.fn()}
        retryError="Не удалось повторить"
        testIdPrefix="recent"
      />,
    )

    expect(screen.getByTestId('recent-project-card-retry')).toBeInTheDocument()
    expect(screen.getByTestId('recent-project-card-retry-error')).toBeInTheDocument()
    expect(screen.queryByTestId('project-card-retry')).toBeNull()
  })
})
