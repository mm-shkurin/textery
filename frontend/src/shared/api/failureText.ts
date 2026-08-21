// Whose text is this, and is it already addressed to the user?
//
// Every screen that catches a failure asks that same question before it renders anything, and two
// of them — the projects feed and the document save — had each answered it in their own module,
// starting from the same two facts and reaching the same two conclusions:
//
//   * A `SessionExpiredError` is not a failure OF the operation. The request was fine and the user
//     is signed out; `authorizedRequest` raises it by identity and `send` rethrows it untouched
//     precisely so a caller can tell those apart. Its own text is the accurate thing to show, and
//     retitling it as "could not save" / "could not load" offers a retry that cannot succeed until
//     the user signs in.
//   * An `HttpError` carries the SERVER's own words — a 4xx `detail`/`message` is a decided answer
//     written for this user, and a bodyless 5xx still contributes its `(HTTP 500)` suffix. Matched
//     with `isHttpError`, never `instanceof`: it is a bare object literal (`httpClient.ts`), not an
//     `Error` at all, so a type-only test collapses it into the generic sentence.
//
// Everything else reaching a catch is transport noise in a language the user did not ask for — a
// dropped connection rejects with `TypeError('Failed to fetch')`, and by the time it arrives the
// type is gone and only English survives.
//
// What each caller keeps is its own COPY: the fallback sentence, and the list of messages the
// feature itself authored (contract guards that reach the catch flattened to a plain `Error`, so
// they are indistinguishable from `Failed to fetch` by type and can only be matched by identity).
// Those are per-screen decisions and were never the duplication; the rule above was.
import { isHttpError } from './httpClient'
import { describeFailure } from './send'
import { SessionExpiredError } from '../session/authorizedRequest'

export interface FailureTextOptions {
  // Whether the SERVER's own words may reach the screen. True for a read, where a 4xx explains
  // something about the request the user made and the fallback explains nothing. False for the
  // document save, whose sentence is not a description of the failure but an instruction —
  // «текст пока только в редакторе, не потеряйте вкладку» — that no server message replaces.
  serverText?: boolean
  // Messages this feature authored itself. `readonly` so the fail-closed direction cannot be
  // widened at runtime: a list another module can `push` onto is one that can be made to leak the
  // English text this function exists to keep off the screen. A guard added later and not listed
  // degrades to the fallback rather than leaking — the safe direction.
  authored?: readonly string[]
}

export function describeOperationFailure(
  failure: unknown,
  fallback: string,
  { authored = [], serverText = true }: FailureTextOptions = {},
): string {
  if (failure instanceof SessionExpiredError) return failure.message
  if (serverText && isHttpError(failure)) return describeFailure(failure, fallback)
  if (failure instanceof Error && authored.includes(failure.message)) return failure.message
  return fallback
}
