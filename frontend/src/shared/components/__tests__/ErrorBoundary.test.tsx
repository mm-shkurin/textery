import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { ErrorBoundary } from '../ErrorBoundary'

function Boom(): never {
  throw new Error('component exploded')
}

function Fine() {
  return <p>содержимое</p>
}

describe('ErrorBoundary', () => {
  // React logs the caught error itself, on top of the boundary's own componentDidCatch. Silenced
  // so an EXPECTED throw does not print a stack that reads like a failing run — restored after,
  // so a genuine unexpected error still surfaces.
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders its children untouched while nothing throws', () => {
    render(
      <ErrorBoundary title="Не удалось">
        <Fine />
      </ErrorBoundary>,
    )

    expect(screen.getByText('содержимое')).toBeInTheDocument()
    expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument()
  })

  // The point of the boundary: a throw becomes a message, not a blank page.
  it('replaces a throwing subtree with its titled message instead of unmounting the tree', () => {
    render(
      <ErrorBoundary title="Редактор не удалось загрузить.">
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByTestId('error-boundary')).toHaveTextContent('Редактор не удалось загрузить.')
  })

  // role="alert", so a screen reader is told rather than left on a silently swapped region.
  it('announces the failure as an alert', () => {
    render(
      <ErrorBoundary title="Редактор не удалось загрузить.">
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
  })

  // There is no reporting sink in this app, so the console is the only trace a crash leaves.
  it('records the error so a crash is not silent', () => {
    render(
      <ErrorBoundary title="Не удалось">
        <Boom />
      </ErrorBoundary>,
    )

    expect(console.error).toHaveBeenCalledWith(
      'Unhandled error in React subtree',
      expect.objectContaining({ message: 'component exploded' }),
      expect.anything(),
    )
  })

  // A button that reloads into the same crash is worse than no button, so recovery is offered
  // only when the caller passed somewhere to go.
  it('offers no recovery action when the caller has nowhere safe to send the user', () => {
    render(
      <ErrorBoundary title="Не удалось">
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  // Recovery is a two-party move, and the test has to model both parties in ONE click: the
  // boundary clears its flag, the caller navigates away from the crashing subtree. React batches
  // both state updates into a single re-render, so the healthy subtree is what gets retried. Swap
  // the children in a later render instead and the boundary re-renders `Boom`, catches again, and
  // stays on the failure screen — which is the boundary working, not failing.
  it('runs the caller-supplied recovery action and clears the failure state', () => {
    const onRecover = vi.fn()

    function Host() {
      const [crashed, setCrashed] = useState(true)
      return (
        <ErrorBoundary
          title="Не удалось"
          recoverLabel="Назад"
          onRecover={() => {
            onRecover()
            setCrashed(false)
          }}
        >
          {crashed ? <Boom /> : <Fine />}
        </ErrorBoundary>
      )
    }

    render(<Host />)
    expect(screen.getByTestId('error-boundary')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Назад' }))

    expect(onRecover).toHaveBeenCalledTimes(1)
    expect(screen.getByText('содержимое')).toBeInTheDocument()
    expect(screen.queryByTestId('error-boundary')).not.toBeInTheDocument()
  })

  it('labels the recovery action with the default wording when the caller supplies none', () => {
    render(
      <ErrorBoundary title="Не удалось" onRecover={vi.fn()}>
        <Boom />
      </ErrorBoundary>,
    )

    expect(screen.getByRole('button', { name: 'Вернуться' })).toBeInTheDocument()
  })
})
