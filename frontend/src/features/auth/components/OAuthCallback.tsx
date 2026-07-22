// STUB (red-frontend 3.1). The /auth/callback interstitial does not exist yet — green-frontend
// implements reading the one-time handoff code from the query, the loading state, and the
// exchange -> store session -> navigate(app-shell, { replace:true }) flow. This empty stub exists
// only so the (skipped) 3.1 test can resolve its import; it renders nothing and drives no behavior.
export function OAuthCallback() {
  return null
}
