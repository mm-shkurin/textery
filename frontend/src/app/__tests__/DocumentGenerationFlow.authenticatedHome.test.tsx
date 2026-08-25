import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { App } from '../App'
import * as projectsApi from '../../features/projects/api/projectsApi'
import { clearSession, saveSession } from '../../shared/session/authSession'

// The landing is the shopfront for people who have no account yet. A signed-in user opening «/»
// has already walked through that door, and showing them the pitch again — «Textery — самая
// быстрая нейросеть», «Попробовать бесплатно» — hides the thing they actually came back for:
// their own projects. So the root surface splits on the session: anonymous gets the landing,
// signed-in gets «Мои проекты».
//
// Asserted through <App /> rather than on the flow component, because the split is only real if
// the ROUTE produces it: rendering ProjectsPage from a test that already knows to render it
// would prove nothing about what «/» does.
vi.mock('../../features/projects/api/projectsApi')

describe('the root surface follows the session', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/')
    vi.mocked(projectsApi.listProjects).mockReturnValue(new Promise(() => {}))
  })

  afterEach(() => {
    clearSession()
    vi.clearAllMocks()
  })

  it('opens «Мои проекты» for a signed-in user instead of the landing', async () => {
    saveSession({ accessToken: 'access-1', refreshToken: 'refresh-1' })

    render(<App />)

    await waitFor(() => expect(screen.getByTestId('projects-screen')).toBeInTheDocument())
    expect(screen.queryByTestId('features-primary-cta-button')).not.toBeInTheDocument()
  })

  it('opens the landing for a visitor with no session', () => {
    render(<App />)

    expect(screen.getByTestId('features-primary-cta-button')).toBeInTheDocument()
    expect(screen.queryByTestId('projects-screen')).not.toBeInTheDocument()
  })
})
