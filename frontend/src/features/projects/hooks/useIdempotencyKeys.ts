import { useMemo, useRef } from 'react'

/**
 * One idempotency key per subject, minted on demand and kept until the subject's attempt is
 * CONFIRMED.
 *
 * It survives a failure on purpose: the failure this guards is the one where the request reached
 * the server and only the response was lost, and a fresh key there would bill a second generation
 * for work already running. It is dropped on success, because the user's next command on that
 * subject is a new one rather than a replay of the one that landed.
 */
export function useIdempotencyKeys() {
  const keys = useRef(new Map<string, string>())

  // Stable across renders: the callbacks that close over this are themselves memoized, and a
  // fresh object here would invalidate every one of them on every render — which is how a
  // memoized card list quietly stops being memoized.
  return useMemo(
    () => ({
      keyFor(subject: string): string {
        const existing = keys.current.get(subject)
        if (existing !== undefined) return existing
        const minted = crypto.randomUUID()
        keys.current.set(subject, minted)
        return minted
      },
      confirm(subject: string): void {
        keys.current.delete(subject)
      },
    }),
    [],
  )
}
