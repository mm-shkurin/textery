// Shared credential fixtures for the real-fetch loginApi test siblings (loginApi.test.ts,
// loginApi.accountLocked.test.ts, loginApi.transportStatus.test.ts). These files stub `fetch` and
// exercise `login()` unmocked. The per-file `fetch` stub builders stay in their own files — each
// names its file's scenario (stubFetchLockout, stubFetchUnparseable, …) and several are
// single-file, so extracting them would trade intent-carrying names for indirection.
//
// `rejectionOf` used to live here too and now lives in `src/test/rejectionOf.ts`: it was never
// about login, and a non-auth feature was already importing it from this login-named module.
//
// NOTE: no `vi.mock` lives here — module mocks are hoisted and file-scoped and must stay per-file.
// Nothing in this module touches global/module state.

export const EMAIL = 'user@example.com'
export const PASSWORD = 'correct-horse'
