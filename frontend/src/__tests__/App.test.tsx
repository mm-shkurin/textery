import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import * as projectsApi from '../features/projects/api/projectsApi'
import { App } from '../app/App'
import * as api from '../features/generation/api/generationApi'
import * as documentApi from '../features/generation/api/documentApi'
import { saveSession, clearSession, getAccessToken } from '../shared/session/authSession'

vi.mock('../features/generation/api/generationApi')
vi.mock('../features/generation/api/documentApi')
vi.mock('../features/projects/api/projectsApi')

// Story 18 unified the create flow: the CTA opens the type modal, and picking a type goes
// STRAIGHT to the generation workspace — no mode-select modal in between.
function pickDokladType() {
  fireEvent.click(screen.getByTestId('projects-toolbar-create'))
  fireEvent.click(screen.getByTestId('type-card-doklad'))
  expect(screen.getByTestId('generation-form')).toBeInTheDocument()
}

// Both destinations behind the landing — the generation workspace and the manual editor — are
// now behind a session: the landing stays public, but its CTA sends an anonymous visitor to
// register instead of opening the type modal. Signing in is therefore SETUP, not subject; every
// flow test below stops at the landing without it. Story 5's tests passed before this because
// the flow was open to anonymous users, which changed by product decision, not by accident.
describe('App step transitions', () => {
  beforeEach(() => {
    vi.mocked(api.createGeneration).mockReturnValue(new Promise(() => {}))
    vi.mocked(documentApi.createDocument).mockReturnValue(new Promise(() => {}))
    // Подписанный пользователь приземляется на «Мои проекты» — лента висит, экран рисуется.
    vi.mocked(projectsApi.listProjects).mockReturnValue(new Promise(() => {}))
    // App renders its own BrowserRouter, and jsdom's location SURVIVES between tests in a
    // file — so the gate tests below, which navigate away, would otherwise leave every later
    // render starting there. Reset the URL, not just the session.
    window.history.pushState({}, '', '/')
    saveSession({ accessToken: 'test-access-token', refreshToken: 'test-refresh-token' })
  })

  afterEach(() => {
    clearSession()
  })

  // The gate this pins is the ONLY reachable path into either destination: neither has a URL of
  // its own, so the CTA is the door. Without this test, deleting the gate breaks nothing visible.
  //
  // It sends them to REGISTER, not to sign in: someone clicking "create a generation" on a
  // public landing is overwhelmingly a new visitor, and answering them with a password prompt
  // asks for a password they do not have yet.
  it('sends an anonymous visitor to the registration page instead of opening the flow', () => {
    clearSession()
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))

    expect(screen.queryByTestId('type-modal')).not.toBeInTheDocument()
    expect(screen.getByTestId('register-submit-button')).toBeInTheDocument()
  })

  it('keeps the landing itself open to an anonymous visitor', () => {
    clearSession()
    render(<App />)

    expect(screen.getByTestId('features-primary-cta-button')).toBeInTheDocument()
  })

  // Returning users are not new users. Without a door of their own, signing in meant knowing to
  // type /login — the CTA now leads to registration, which is the wrong screen for them.
  it('offers a signed-out visitor a way to sign in', () => {
    clearSession()
    render(<App />)

    fireEvent.click(screen.getByTestId('header-login-button'))

    expect(screen.getByTestId('login-submit-button')).toBeInTheDocument()
  })

  // The two doors are mutually exclusive: "Войти" on a signed-in header offers to start a
  // session that already exists, and the account menu — which holds sign-out — takes its place.
  it('hides the sign-in action once a session exists', () => {
    render(<App />)

    expect(screen.queryByTestId('header-login-button')).not.toBeInTheDocument()
    expect(screen.getByTestId('projects-profile-button')).toBeInTheDocument()
  })

  it('walks projects -> type -> generation workspace, no mode modal in between', () => {
    render(<App />)

    pickDokladType()

    expect(screen.getByTestId('generation-form')).toBeInTheDocument()
    expect(screen.queryByTestId('mode-modal')).not.toBeInTheDocument()
  })

  // Закрытие модалки возвращает туда, откуда её открыли, — а для сессии это «Мои проекты».
  it('closing the type modal returns to the projects screen', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('projects-toolbar-create'))
    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(screen.queryByTestId('type-modal')).not.toBeInTheDocument()
    expect(screen.getByTestId('projects-screen')).toBeInTheDocument()
  })

  // Story 18 removed the mode-select modal, and with it the manual-mode card that used to be the
  // create-path entry into ManualEditor. The editor stays reachable from history (scenario 6.1
  // will add a fresh blank-page entry), and its behaviour is covered by the ManualEditor.* suite;
  // the App-level integration tests that drove it through the deleted mode modal are dropped here.

  // Signing out from inside the workspace must both drop the tokens AND unwind the flow.
  // Asserting only the tokens would pass while leaving the user's document on screen behind an
  // ended session; asserting only the screen would pass while leaving the tokens in storage.
  it('signing out from the workspace clears the session and returns to the landing', () => {
    render(<App />)
    pickDokladType()
    expect(screen.getByTestId('generation-form')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('workspace-profile-button'))
    fireEvent.click(screen.getByTestId('workspace-logout-button'))

    expect(getAccessToken()).toBeNull()
    expect(screen.queryByTestId('generation-form')).not.toBeInTheDocument()
    expect(screen.getByTestId('features-primary-cta-button')).toBeInTheDocument()
  })
})
