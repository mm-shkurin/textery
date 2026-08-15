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
    expect(onRetry).toHaveBeenCalledWith(GENERATION.id)
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
