import { useCallback, useState } from 'react'

export type ProjectView = 'grid' | 'list'

// Per-device, not per-account: the choice is about the screen in front of the user, and putting
// it on the server would make it a cross-request read-modify-write for a preference that nobody
// needs to share between their laptop and their phone.
export const VIEW_STORAGE_KEY = 'textery.projects.view'

const DEFAULT_VIEW: ProjectView = 'grid'

function readStoredView(): ProjectView {
  try {
    // A value this build does not recognise falls back to the default rather than being
    // rendered: an older or hand-edited entry must not leave the feed with no view at all.
    return window.localStorage.getItem(VIEW_STORAGE_KEY) === 'list' ? 'list' : DEFAULT_VIEW
  } catch {
    // Storage throws rather than returning null in a private-mode Safari and under some
    // enterprise policies. A view preference is not worth failing the page over.
    return DEFAULT_VIEW
  }
}

/** The grid/list choice, remembered on this device across reloads. */
export function useProjectView(): [ProjectView, (view: ProjectView) => void] {
  const [view, setView] = useState<ProjectView>(readStoredView)

  const choose = useCallback((next: ProjectView) => {
    setView(next)
    try {
      window.localStorage.setItem(VIEW_STORAGE_KEY, next)
    } catch {
      // Same reason as above: the toggle still works for this session.
    }
  }, [])

  return [view, choose]
}
