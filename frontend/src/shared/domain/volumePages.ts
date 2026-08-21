/**
 * How long a generated work may be, and the choices a picker offers for it.
 *
 * In `shared/` for the reason `textStyles` is: TWO features name these bounds now.
 * Generation collects the length on the composer form; projects re-chooses it on
 * «изменить объём» when retrying a failed run. A copy in each is how the retry card
 * ends up offering a length the composer would have refused.
 *
 * The numbers mirror the domain's own (`generation_rules.MIN_VOLUME_PAGES` /
 * `MAX_VOLUME_PAGES`). Mirrored rather than fetched: a control that cannot be
 * rendered until a round trip answers is worse than one that can drift, and the
 * server refuses out-of-range values regardless — this is the courtesy layer, not
 * the guard.
 */

export const MIN_VOLUME_PAGES = 1
export const MAX_VOLUME_PAGES = 10

// The mockup's default (`<input type="number" min="1" max="10" value="5">`) and the value the
// client hardcoded before the field existed, so an untouched form still asks for what it always
// asked for.
export const DEFAULT_VOLUME_PAGES = 5

/** True when the volume is an integer inside the range the server accepts. */
export function isVolumeAcceptable(volumePages: number): boolean {
  return (
    Number.isInteger(volumePages) &&
    volumePages >= MIN_VOLUME_PAGES &&
    volumePages <= MAX_VOLUME_PAGES
  )
}

/**
 * Every length a picker may offer, derived from the bounds rather than listed.
 *
 * A hand-written list is one edit away from disagreeing with `isVolumeAcceptable`
 * sitting five lines above it — and the disagreement shows up as an option the
 * server refuses, which the user reads as a broken control.
 */
export const VOLUME_PAGE_OPTIONS: readonly number[] = Array.from(
  { length: MAX_VOLUME_PAGES - MIN_VOLUME_PAGES + 1 },
  (_unused, index) => MIN_VOLUME_PAGES + index,
)
