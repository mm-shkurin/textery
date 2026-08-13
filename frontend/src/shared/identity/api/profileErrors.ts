// The save failed for a reason the USER can act on: the backend refused the value with a 400
// `{error_code, message}`. Rendered inline under the field, never as the "could not reach the
// server" banner — the two are different stories and only one of them is the user's to fix.
//
// Its own module so the dev stub can throw it without importing the client that calls the stub.
// The uploaded image was refused for a reason the user can act on: too many bytes, a type the
// server does not decode, or pixel dimensions past its bound. Same shape as the name's refusal
// and deliberately a DIFFERENT class — the two are shown in different places on the screen, and
// one `catch` that could not tell them apart would put an image complaint under the name field.
export class AvatarRejectedError extends Error {
  readonly errorCode: string
  constructor(errorCode: string, message: string) {
    super(message)
    this.name = 'AvatarRejectedError'
    this.errorCode = errorCode
  }
}

export class NameRejectedError extends Error {
  readonly errorCode: string
  constructor(errorCode: string, message: string) {
    super(message)
    this.name = 'NameRejectedError'
    this.errorCode = errorCode
  }
}
