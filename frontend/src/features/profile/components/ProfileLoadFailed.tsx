import { LOAD_FAILED_BODY, LOAD_FAILED_TITLE } from '../profileCopy'

interface ProfileLoadFailedProps {
  onRetry: () => void
  onBack: () => void
}

// Mockup 06. The screen ENDS in a message with a way forward, never in a spinner that keeps
// turning: an unbounded spinner is indistinguishable from a hung tab, and `GET /me` can genuinely
// never answer.
//
// The failure did not end the session — see identityRequest.ts — so the header above this is a
// working menu with a working «Выйти», not a redirect to the login screen.
export function ProfileLoadFailed({ onRetry, onBack }: ProfileLoadFailedProps) {
  return (
    <div className="profile-state" data-testid="profile-load-failed">
      <h2 className="profile-state-title" role="alert">
        {LOAD_FAILED_TITLE}
      </h2>
      <p className="profile-state-body">{LOAD_FAILED_BODY}</p>
      <div className="profile-state-actions">
        <button
          type="button"
          className="profile-btn-primary"
          data-testid="profile-load-retry"
          onClick={onRetry}
        >
          Повторить
        </button>
        {/* «Назад» rather than the mockup's «К проектам»: «Мои проекты» is a step of the flow's
            internal state and has no URL of its own, so a link to it would have to invent one.
            Browser history is the honest destination until that screen gets a route. */}
        <button type="button" className="profile-btn-ghost" onClick={onBack}>
          Назад
        </button>
      </div>
    </div>
  )
}
