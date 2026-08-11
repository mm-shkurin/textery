// The quota-state read the editor route owes on document open.
//
// CONTRACT GAP (recorded by scenario 0.2's `red-selenium`): none of `endpoints.md`'s seven
// endpoints reports quota state. `resets_at` exists only inside the 429 body of
// `POST /ai-edits` — i.e. only AFTER the user has already typed an instruction and been
// refused. The scenario requires the composer to be dead on arrival, so the client needs the
// same fact BEFORE the first attempt. Hence a read of its own.
//
// Deliberately account-scoped, not document-scoped: the daily edit quota belongs to the
// account, and threading a `documentId` through would invite a per-document reading of a
// limit that is not per-document.
//
// RED-phase stub. `red-frontend-api` owns the wire mapping (path, response shape, the
// snake_case→camelCase translation) and green owes the endpoint behind it; this module exists
// now only so the component layer has a real module identity to mock and a real type to agree
// with. It intentionally throws rather than returning a plausible default — a stub that
// answered `{ exhausted: false }` would let a component ship that never reads quota at all.
// A discriminated union, not `{ exhausted: boolean; resetsAt: string | null }`. The loose shape
// made `{ exhausted: true, resetsAt: null }` — an exhausted quota that cannot say when it lifts,
// i.e. a reset hint with nothing to put in `data-resets-at` — a representable value scoped by
// comment alone. Here it does not compile, and the exhausted branch reads `resetsAt` as a
// `string` without a null check no test could ever reach.
//
// `resetsAt` is the wire string, VERBATIM. Not a Date, not a re-serialized ISO string: the
// Selenium layer asserts `data-resets-at` is byte-equal to the instant the API itself returned,
// and a parse/re-format round trip through `Date` is exactly what breaks that equality
// (`+03:00` → `Z`, dropped fractional seconds). Formatting for humans is the countdown's job and
// happens in a sibling element.
export type EditQuotaState =
  { exhausted: false; resetsAt: null } | { exhausted: true; resetsAt: string }

export async function loadEditQuota(): Promise<EditQuotaState> {
  throw new Error('loadEditQuota is not implemented yet')
}
