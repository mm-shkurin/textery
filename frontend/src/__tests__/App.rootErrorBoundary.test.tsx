import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from '../app/App'

// LoginForm is the stand-in for "any non-editor route": auth, landing and history all render
// outside DocumentGenerationFlow's boundary, so before the root boundary existed a throw in any
// of them unmounted the whole tree and left a blank white page. Making this one route throw
// proves the root boundary covers that whole class of routes, not just this component.
vi.mock('../features/auth/components/LoginForm', () => ({
  LoginForm: () => {
    throw new Error('route exploded')
  },
}))

describe('App root error boundary', () => {
  // React logs the caught error on top of the boundary's own componentDidCatch. Silenced so an
  // EXPECTED throw does not print a stack that reads like a failing run; restored after.
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows a message instead of a blank page when a non-editor route throws', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Что-то пошло не так. Обновите страницу.')
  })

  // Nowhere safe to send the user from the root, so no button — one that re-renders the same
  // crash would be worse than none.
  it('offers no recovery action at the root', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
