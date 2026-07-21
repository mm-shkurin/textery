// Structural guards for reading fields off an `unknown` rejection. The auth apis type their
// rejections as `unknown` because at run time nothing holds the error to a declared shape, so each
// reader must earn a field with an `in`/typeof guard rather than an `as` cast. Shared by
// loginErrorHandling and verifyErrorHandling so the object/null dance has one testable home.

// One narrowing guard for "this unknown rejection carries field K": a match narrows the type so
// `error[key]` is reachable, without re-spelling the object/null check and without a cast.
export function hasProp<K extends string>(error: unknown, key: K): error is Record<K, unknown> {
  return typeof error === 'object' && error !== null && key in error
}

// "This rejection carries errorCode === code" — the field the auth forms branch on.
export function hasErrorCode(error: unknown, code: string): boolean {
  return hasProp(error, 'errorCode') && error.errorCode === code
}
