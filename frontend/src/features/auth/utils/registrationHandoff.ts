// The credentials RegisterForm hands to the verification screen, so a freshly verified account
// lands in the app already signed in instead of being asked for a password it typed a minute ago.
//
// WHY THIS EXISTS AT ALL: `POST /api/v1/auth/verify` answers `{is_verified: true}` and no tokens
// (verified against the live backend 2026-07-17). Verification does not create a session. The
// only route to one is `POST /auth/login`, which needs the password — so to land verified users
// in the app, the password has to survive the trip from /register to /verify. Nothing else here
// is negotiable; where it survives is.
//
// IN MEMORY ONLY, and that is the entire design. Every other place we could put it is worse:
//   - router state → React Router serializes it into `window.history.state`, which the browser
//     persists to disk for session restore. That is a password at rest, outliving the tab.
//   - sessionStorage → same problem, plus it is readable by any script on the origin for the
//     whole tab lifetime, when it is needed for about two seconds.
// A module variable dies with the page and cannot be restored. A reload therefore LOSES it and
// the user signs in by hand — an inconvenience deliberately chosen over a password on disk.
//
// The right fix is the backend issuing tokens from /auth/verify, which would delete this file.
// Until then this is a documented trade-off, not an oversight.
interface PendingRegistration {
  email: string
  password: string
}

let pending: PendingRegistration | null = null

export function rememberRegistration(email: string, password: string): void {
  pending = { email, password }
}

// Returns the password ONCE, and only for the account it was stored for.
//
// The email check is not ceremony: /verify takes an email from router state, so without it a
// handoff left by one registration could be spent logging into a different account whose code
// the user happens to hold. Single-use for the same reason a password should not linger — the
// one caller needs it once.
export function consumeRegistration(email: string): string | null {
  if (!pending || pending.email !== email) {
    return null
  }
  const { password } = pending
  pending = null
  return password
}

export function forgetRegistration(): void {
  pending = null
}
