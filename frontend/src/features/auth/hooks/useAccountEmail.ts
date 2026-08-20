import { useIdentity } from '../../../shared/identity/useIdentity'

// The signed-in account's address, from `GET /api/v1/auth/me`.
//
// It used to be DECODED from the access token, because there was no endpoint to ask (see the
// history note in `shared/session/accountEmail.ts`). Story 13 built one, and the token is no longer
// consulted for identity anywhere.
//
// It returns null both while the request is in flight and after it has failed. That is enough for
// a caller that only wants the address and has one way to say "not available"; a caller that must
// tell «загрузка» from «отказ» apart — the header does, because a silent failure would read as an
// account with no name — reads `useIdentity()` and switches on `status`.
export function useAccountEmail(): string | null {
  return useIdentity().profile?.email ?? null
}
