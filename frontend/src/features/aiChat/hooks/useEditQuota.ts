import { useEffect, useRef, useState } from 'react'
import { loadEditQuota, type EditQuotaState } from '../api/editQuotaApi'

// Reads the account's daily edit quota once per mount of the editor route.
//
// `null` means NOT YET KNOWN — the read is in flight, or it failed. Both are the same fact to
// this feature's callers: nothing may claim the account can or cannot edit. A distinct `failed`
// state belongs to scenario 8.8, which owns the quota read's own loading and failure screens;
// inventing one here would ship a branch no test reaches.
//
// Account-scoped: `loadEditQuota` takes no arguments. The daily limit belongs to the account,
// and threading the open document's id through would invite a per-document reading of it.
export function useEditQuota(): EditQuotaState | null {
  const [quota, setQuota] = useState<EditQuotaState | null>(null)

  // Guards the FETCH, not the setState. StrictMode (main.tsx, and the component test's own
  // wrapper) double-invokes effects, so without this the read fires twice per mount. The
  // cancel-flag pattern in `generation/hooks/useDocumentInit` does not serve here: it suppresses
  // the second run's setState while its request still goes out, and the request is what the
  // call-count assertions measure. Hence a ref placed BEFORE the call.
  const requestedRef = useRef(false)

  useEffect(() => {
    if (requestedRef.current) return
    requestedRef.current = true

    loadEditQuota()
      .then(setQuota)
      // A failed read leaves the quota unknown, which is what `null` already says. It is caught
      // rather than left to reject so a dead quota endpoint cannot take the whole route down.
      .catch(() => setQuota(null))
  }, [])

  return quota
}
