import { lazy, Suspense } from 'react'
import { DOCUMENT_TYPE_LABELS } from '../shared/documentTypes'
import { HistoryPage } from '../features/history/components/HistoryPage'
import { LandingPage } from '../features/landing/components/LandingPage'
import { ChatWorkspace } from '../features/generation/components/ChatWorkspace'
import { ErrorBoundary } from '../shared/components/ErrorBoundary'
import { FlowLanding } from './FlowLanding'
import { useFlowNavigation } from './useFlowNavigation'

// The ONE lazy boundary in the app, and it is drawn here on weight rather than on taste:
// ManualEditor pulls Tiptap + ProseMirror, by far the largest dependency in the tree, and it is
// reached only by picking manual mode — a landing visitor, the whole auth flow, history and the
// chat workspace never touch it. Statically imported it rode in the single entry chunk, so every
// first paint paid for an editor most sessions never open.
//
// Deliberately NOT applied per route: the auth screens and the landing are small enough that
// splitting them would trade one chunk for several round trips without shrinking anything that
// matters.
const ManualEditor = lazy(() =>
  import('../features/generation/components/ManualEditor').then((module) => ({
    default: module.ManualEditor,
  })),
)

// Which screen for which state, and nothing else — every transition and its reasoning lives in
// useFlowNavigation.
//
// The landing is the public shopfront and stays open to anonymous visitors; gating it would be
// gating marketing. Everything BEHIND it (type → the generation workspace, or the editor opened
// from history) needs an account.
//
// The gate below is CLIENT-SIDE ONLY: it decides what UI to render and protects nothing on its
// own. Neither destination has a URL of its own — both are internal state — so the CTA is the
// only way in, and gating the CTA closes the reachable path. A user who edits their own memory,
// or calls the API directly, walks straight past it.
//
// UPDATE 2026-07-17: the backend now enforces this for real, so the gate is no longer the only
// thing between an anonymous caller and a document. Re-measured by curl against the running
// stack — the earlier note here said the hole was open, and it is now closed:
//   POST /api/v1/generations, no header        -> 401 UNAUTHORIZED
//   POST /api/v1/generations, "Bearer garbage" -> 401 UNAUTHORIZED
//   POST /api/v1/documents,   no header        -> 401 UNAUTHORIZED
// This is still a product gate rather than the security boundary — the boundary is the 401.
// Keep them distinct: if the client's check is removed, the backend still refuses; if the
// backend's is removed, this one refuses nothing.
export function DocumentGenerationFlow() {
  const flow = useFlowNavigation()
  const { step, documentType, mode, isAuthenticated } = flow

  // Belt and braces: the CTA is the only path that sets a non-landing step, but a session can
  // end mid-flow (storage cleared, a refresh that failed). Re-checking here means an expired
  // session collapses to the landing rather than leaving a workspace or an editor on screen
  // that every request will refuse.
  if (step !== 'landing' && !isAuthenticated) {
    return <LandingPage onPrimaryCtaClick={flow.startFlow} onLoginClick={flow.goToLogin} />
  }

  // Below the isAuthenticated gate on purpose: history is owner-scoped by construction (both
  // endpoints 401 without a token), so it never renders for a signed-out visitor.
  if (step === 'history') {
    return <HistoryPage onOpenDocument={flow.openDocumentFromHistory} onBack={flow.backToLanding} />
  }

  if (step === 'form' && documentType && mode) {
    const documentTypeLabel = DOCUMENT_TYPE_LABELS[documentType]

    // Story 18, scenario 2.1: a completed generation becomes the editor BY ITSELF. The user
    // watched the text being written; making them press "открыть в редакторе" afterwards asks
    // them to confirm the thing they already asked for, and the read-only render they would be
    // confirming from is indistinguishable from the editor at a glance.
    //
    // Gated on `content` as well as on the state, deliberately: the whole point of the swap is
    // that the generated text carries across it, and `doc-body` — the last surface still showing
    // that text — goes away with the workspace. Opening an EMPTY editor here would not be a
    // cosmetic miss, it would read as "it deleted my report", so a completed generation that
    // somehow carries no text keeps the read-only surface rather than losing it silently.
    const generatedContent = flow.generation.state === 'completed' ? flow.generation.content : null

    // Named because the disjunction is not one idea but two, and nothing in the operator says so:
    // the editor is either the mode the user CHOSE (the history-open path sets mode='manual') or
    // the place a finished generation ARRIVED at (nobody chose anything). Neither side implies the
    // other, and either alone is enough.
    const opensEditor = mode === 'manual' || generatedContent !== null

    if (opensEditor) {
      // ManualEditor takes no sign-out action: it had none on Story 5's branch, and a merge is
      // not the place to invent one. That leaves the editor as the one signed-in screen with no
      // way out of the session — a real gap, but a NEW one, created by combining the branches
      // rather than present in either. It belongs to a follow-up.
      // The fallback says what is happening rather than showing a blank frame: the chunk is
      // fetched at the moment manual mode is chosen, and on a slow link that is a visible wait.
      // Boundary OUTSIDE Suspense so it catches both failures the lazy path can produce: a
      // rejected chunk fetch (offline mid-session) and a throw from inside the editor once it
      // mounts. Recovery goes back through backFromEditor (history for an opened document) — a
      // real destination, not a reload into the same crash.
      return (
        <ErrorBoundary
          title="Редактор не удалось загрузить."
          recoverLabel="Вернуться назад"
          onRecover={flow.backFromEditor}
        >
          <Suspense fallback={<p className="editor-loading">Загрузка редактора…</p>}>
            <ManualEditor
              documentType={documentType}
              documentTypeLabel={documentTypeLabel}
              onBack={flow.backFromEditor}
              existingDocumentId={flow.openDocumentId ?? undefined}
              generatedContent={generatedContent ?? undefined}
            />
          </Suspense>
        </ErrorBoundary>
      )
    }

    return (
      <ChatWorkspace
        documentType={documentType}
        documentTypeLabel={documentTypeLabel}
        state={flow.generation.state}
        content={flow.generation.content}
        volumePages={flow.generation.volumePages}
        createdAt={flow.generation.createdAt}
        error={flow.generation.error}
        onSubmit={flow.submitGeneration}
        onReset={flow.generation.reset}
        onLogoutClick={flow.handleLogout}
      />
    )
  }

  return (
    <FlowLanding
      step={step as 'landing' | 'type'}
      isAuthenticated={isAuthenticated}
      onPrimaryCtaClick={flow.startFlow}
      onLoginClick={flow.goToLogin}
      onLogoutClick={flow.handleLogout}
      onHistoryClick={flow.openHistory}
      onSelectType={flow.selectType}
      onClose={flow.closeToLanding}
    />
  )
}
