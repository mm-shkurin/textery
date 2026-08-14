import { useCallback, useState } from 'react'
import { readStored, writeStored } from '../../../shared/lib/browser'

export type ProjectView = 'grid' | 'list'

// Per-device, not per-account: the choice is about the screen in front of the user, and putting
// it on the server would make it a cross-request read-modify-write for a preference that nobody
// needs to share between their laptop and their phone.
export const VIEW_STORAGE_KEY = 'textery.projects.view'

const DEFAULT_VIEW: ProjectView = 'grid'

function readStoredView(): ProjectView {
  // A value this build does not recognise falls back to the default rather than being rendered:
  // an older or hand-edited entry must not leave the feed with no view at all. `readStored`
  // already answers null off-browser and where storage throws.
  return readStored('local', VIEW_STORAGE_KEY) === 'list' ? 'list' : DEFAULT_VIEW
}

/** The grid/list choice, remembered on this device across reloads. */
export function useProjectView(): [ProjectView, (view: ProjectView) => void] {
  const [view, setView] = useState<ProjectView>(readStoredView)

  const choose = useCallback((next: ProjectView) => {
    setView(next)
    // A refused write still leaves the toggle working for this session.
    writeStored('local', VIEW_STORAGE_KEY, next)
  }, [])

  return [view, choose]
}
