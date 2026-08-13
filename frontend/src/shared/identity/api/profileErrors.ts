// The save failed for a reason the USER can act on: the backend refused the value with a 400
// `{error_code, message}`. Rendered inline under the field, never as the "could not reach the
// server" banner — the two are different stories and only one of them is the user's to fix.
//
// Its own module so the dev stub can throw it without importing the client that calls the stub.
export class NameRejectedError extends Error {
  readonly errorCode: string
  constructor(errorCode: string, message: string) {
    super(message)
    this.name = 'NameRejectedError'
    this.errorCode = errorCode
  }
}
