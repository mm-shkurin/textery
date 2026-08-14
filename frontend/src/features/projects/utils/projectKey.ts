import type { ProjectSummary } from '../api/projectsApi'

// A project's identity, in one place because both consumers of it explain the same hazard: the
// two arms of the merged feed come from different tables, so `id` alone is NOT unique — the
// fixture's document and generation both carry id '1'. Keying or addressing a card on `id` would
// collapse the pair onto one node. Named here so the rule is stated once rather than re-derived
// as an inline template literal at each site.
//
// Its own module rather than an export from `ProjectCard.tsx`: a file that exports both a
// component and a plain function loses React Fast Refresh for that component (the whole module is
// re-evaluated on edit and remounts), which is what `react/only-export-components` reports.
export function projectKey(project: ProjectSummary): string {
  return `${project.kind}-${project.id}`
}
