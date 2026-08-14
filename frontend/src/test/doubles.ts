// The two places a test is allowed to step outside the type system, with the reason written down.
//
// The jury's remark was `as unknown as` scattered through fixtures and doubles — a cast that
// silences the compiler wherever it is written, so nothing distinguishes "this stands in for a
// browser object with forty members I do not need" from "this fixture is quietly the wrong type".
// Both uses are legitimate; both belong in one named place that says which is which.

/**
 * A stand-in for an object the test only touches a few members of — an editor view, a canvas
 * context, a DOM event.
 *
 * The cast is unavoidable: the real types describe the whole browser API, and implementing forty
 * members to assert on two would be a worse test. What this adds is a name at every call site,
 * so a reader sees "partial double" instead of a cast that could mean anything.
 */
export function partialDouble<T>(members: object): T {
  return members as T
}

/**
 * A value as it actually arrives from the network: JSON text, parsed.
 *
 * Wire types are a compile-time claim about a runtime body — `updatedAt: string` says nothing
 * about what the server sends. A fixture representing a malformed response must therefore be able
 * to hold a number, a null or nonsense where the type promises a string, and casting the literal
 * would state the opposite of what the fixture is for. Parsing JSON is where an untyped value
 * legitimately becomes a typed one, which is exactly the boundary being tested.
 */
export function fromWire<T>(json: string): T {
  return JSON.parse(json) as T
}

/**
 * A stand-in that is not an object literal — a stubbed browser function, a rejection value that is
 * deliberately not an Error. Same contract as `partialDouble`, for the cases where "partial" does
 * not describe what is happening: the value is a whole substitute, just not of the declared type.
 */
export function stubbed<T>(value: unknown): T {
  return value as T
}
