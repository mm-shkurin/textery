// MM:SS for a countdown. Clamps at zero so an expired/negative deadline renders "00:00" rather
// than "-1:59" garbage, and floors so a fractional second never shows as ":60". A non-finite
// input (a missing Retry-After that reached here as NaN) is the caller's bug to guard BEFORE this
// — but we still refuse to emit "NaN:NaN": treat it as zero.
export function formatMmSs(totalSeconds: number): string {
  const safe = Number.isFinite(totalSeconds) ? Math.max(0, Math.floor(totalSeconds)) : 0
  const minutes = Math.floor(safe / 60)
  const seconds = safe % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}
