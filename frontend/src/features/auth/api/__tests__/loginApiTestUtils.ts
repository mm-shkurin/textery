// Shared fixtures/helpers for the real-fetch loginApi test siblings (loginApi.test.ts,
// loginApi.accountLocked.test.ts, loginApi.transportStatus.test.ts). These files stub `fetch` and
// exercise `login()` unmocked; the credential fixtures and the reject-capturing helper were
// byte-identical across all three. The per-file `fetch` stub builders stay in their own files —
// each names its file's scenario (stubFetchLockout, stubFetchUnparseable, …) and several are
// single-file, so extracting them would trade intent-carrying names for indirection.
//
// NOTE: no `vi.mock` lives here — module mocks are hoisted and file-scoped and must stay per-file.
// Nothing in this module touches global/module state; `rejectionOf` is pure.

export const EMAIL = 'user@example.com'
export const PASSWORD = 'correct-horse'

export async function rejectionOf(promise: Promise<unknown>): Promise<unknown> {
  try {
    await promise
  } catch (error) {
    return error
  }
  throw new Error('expected login() to reject, but it resolved')
}
