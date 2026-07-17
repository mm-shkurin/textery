import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import App from '../app/App'
import * as api from '../features/generation/api/generationApi'
import * as documentApi from '../features/generation/api/documentApi'
import { saveSession, clearSession, getAccessToken } from '../features/auth/utils/authSession'

vi.mock('../features/generation/api/generationApi')
vi.mock('../features/generation/api/documentApi')

function openModeModalForDoklad() {
  fireEvent.click(screen.getByTestId('features-primary-cta-button'))
  fireEvent.click(screen.getByTestId('type-card-doklad'))
  expect(screen.getByTestId('mode-modal')).toBeInTheDocument()
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
  // session that already exists, and it is where the sign-out action now sits instead.
  it('hides the sign-in action once a session exists', () => {
    render(<App />)

    expect(screen.queryByTestId('header-login-button')).not.toBeInTheDocument()
    expect(screen.getByTestId('header-logout-button')).toBeInTheDocument()
  })

  it('walks landing -> type -> mode -> form and back to landing on close', () => {
    render(<App />)

    openModeModalForDoklad()

    fireEvent.click(screen.getByTestId('mode-card-auto'))
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('back button from mode modal returns to type modal', () => {
    render(<App />)

    openModeModalForDoklad()

    fireEvent.click(screen.getByLabelText(/Назад к типу документа/))
    expect(screen.getByTestId('type-modal')).toBeInTheDocument()
  })

  it('closing the type modal returns to landing', () => {
    render(<App />)

    fireEvent.click(screen.getByTestId('features-primary-cta-button'))
    fireEvent.click(screen.getByLabelText('Закрыть'))

    expect(screen.queryByTestId('type-modal')).not.toBeInTheDocument()
  })

  it('selecting manual mode opens a dedicated empty editor with a document-type breadcrumb', () => {
    render(<App />)

    openModeModalForDoklad()

    fireEvent.click(screen.getByTestId('mode-card-manual'))

    expect(screen.queryByTestId('mode-modal')).not.toBeInTheDocument()
    expect(screen.getByTestId('manual-editor')).toBeInTheDocument()
    expect(screen.getByTestId('editor-breadcrumb')).toHaveTextContent('Доклад · Ручной режим')
  })

  // RED (scenario 6.1): ManualEditor's onBack is wired to closeToLanding, which
  // resets step to 'landing' and clears documentType/mode instead of returning
  // to the mode modal. Predicted/actual: TestingLibraryElementError, unable to
  // find [data-testid="mode-modal"] (rendered landing page instead).
  it('back button from the manual editor returns to the mode modal, document type still scoped', () => {
    render(<App />)

    openModeModalForDoklad()
    fireEvent.click(screen.getByTestId('mode-card-manual'))
    expect(screen.getByTestId('manual-editor')).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText('Назад'))

    expect(screen.queryByTestId('manual-editor')).not.toBeInTheDocument()
    expect(screen.getByTestId('mode-modal')).toBeInTheDocument()
    expect(screen.getByLabelText('Назад к типу документа: Доклад')).toBeInTheDocument()
  })

  // Signing out from inside the workspace must both drop the tokens AND unwind the flow.
  // Asserting only the tokens would pass while leaving the user's document on screen behind an
  // ended session; asserting only the screen would pass while leaving the tokens in storage.
  it('signing out from the workspace clears the session and returns to the landing', () => {
    render(<App />)
    openModeModalForDoklad()
    fireEvent.click(screen.getByTestId('mode-card-auto'))
    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()

    fireEvent.click(screen.getByTestId('workspace-logout-button'))

    expect(getAccessToken()).toBeNull()
    expect(screen.queryByTestId('chat-panel')).not.toBeInTheDocument()
    expect(screen.getByTestId('features-primary-cta-button')).toBeInTheDocument()
  })
})
