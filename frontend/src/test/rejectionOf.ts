// Awaits a promise that the test expects to REJECT and hands back the thrown value.
//
// Promoted here out of `features/auth/api/__tests__/loginApiTestUtils.ts` once the fourth feature
// needed it: the helper never had anything to do with login, and `oauthExchangeApi.test.ts` was
// already importing it across a feature boundary from a file named after a different one.
//
// The throw on the resolve path is the whole point, and why this is preferred over the inline
// `promise.catch((error: unknown) => error)` it replaces: that form silently yields the RESOLVED
// value when the call under test does not reject, so the follow-up assertion reports "expected
// {documentId: …} to be an instance of DocumentNotFoundError" — a confusing complaint about a
// value's type when the real defect is that no error was raised at all.
export async function rejectionOf(promise: Promise<unknown>): Promise<unknown> {
  let resolved: unknown
  try {
    resolved = await promise
  } catch (error) {
    return error
  }
  throw new Error(`expected the call under test to reject, but it resolved with ${String(resolved)}`)
}
