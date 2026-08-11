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
import { send } from '../../../shared/api/send'

//
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

// Deliberately NOT `{ notFound: true }`. A 404 here means the quota ENDPOINT is missing, not that
// a document is, and DocumentNotFoundError would send the user to look for work that is fine.
const FALLBACK = 'Не удалось загрузить лимит правок'

// The wire shape, read as unknown keys rather than a declared interface: a declared response type
// is a promise the SERVER makes, not one the compiler can keep, and every guard below exists
// because the server can break it.
interface QuotaWire {
  exhausted?: unknown
  resets_at?: unknown
}

// Silence must REFUSE, never default to "there is room". `performRequest` ends with
// `res.json().catch(() => ({}))`, so a 204, an empty 200 and an HTML page served with a 200 all
// arrive here as `{}` — and `Boolean(body.exhausted)` would answer "the quota has room" from an
// endpoint that said nothing, putting the composer live. That is the exact state Scenario 0.2
// exists to prevent, so anything the wire did not clearly state is a load failure.
//
// `resets_at` is checked for PRESENCE and for TYPE, not merely against `null`: an absent key
// yields `resetsAt: undefined` (`data-resets-at="undefined"`) and an epoch number or `''` types
// itself `string` by declaration alone while the Selenium byte-equality then passes trivially on
// matching garbage. Both are refusals, not values.
function mapQuota(body: QuotaWire): EditQuotaState {
  const { exhausted, resets_at: resetsAt } = body
  if (typeof exhausted !== 'boolean') {
    throw new Error(FALLBACK)
  }
  if (resetsAt !== null && (typeof resetsAt !== 'string' || !resetsAt)) {
    throw new Error(FALLBACK)
  }
  if (!exhausted) {
    // Dropped, not forwarded: the within-quota arm types `resetsAt` as exactly `null`, so a server
    // that sends an instant alongside room would otherwise produce a value that lies about itself.
    return { exhausted: false, resetsAt: null }
  }
  if (resetsAt === null) {
    // An exhausted quota that cannot say when it lifts — a reset hint with nothing to count to.
    throw new Error(FALLBACK)
  }
  // VERBATIM. No Date round trip anywhere: `+03:00` → `Z` is what breaks the Selenium equality.
  return { exhausted: true, resetsAt }
}

export async function loadEditQuota(): Promise<EditQuotaState> {
  return mapQuota(await send<QuotaWire>('/api/v1/ai-edits/quota', {}, FALLBACK))
}
