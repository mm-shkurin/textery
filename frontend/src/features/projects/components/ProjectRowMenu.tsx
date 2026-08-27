import type { ProjectSummary } from '../api/projectsApi'
import { documentTypeLabelFromWire } from '../../../shared/copy/documentTypeCopy'
import { ProjectCardMenu, type ProjectActions } from './ProjectCardMenu'
import projectsPageStyles from './ProjectsPage.module.css'

interface ProjectRowMenuProps {
  project: ProjectSummary
  /** The row's label, already resolved from title / preview / type by the renderer. */
  label: string
  /** The renderer's testid namespacer, so the rail and the full list stay distinguishable. */
  namespaced: (name: string) => string
  actions?: ProjectActions
}

/**
 * The «···» menu, under the one rule that decides whether a row has one.
 *
 * The grid (`ProjectCard`) and the list (`ProjectsTable`) are two renderings of the
 * same row, and each carried its own copy of both the guard and the six props. The
 * guard is the part worth writing once: a menu appears only where the feed can
 * re-read itself (`actions !== undefined`) AND the row is a document — a generation
 * has no name to edit and nothing to delete, so the button is absent rather than
 * disabled, because a disabled button promises a menu that will never come.
 *
 * Two copies of a rule with two conditions is how one renderer keeps offering rename
 * on a row the other has already stopped offering it on.
 */
export function ProjectRowMenu({ project, label, namespaced, actions }: ProjectRowMenuProps) {
  if (actions === undefined || project.kind !== 'document') return null
  return (
    <ProjectCardMenu
      documentId={project.id}
      title={label}
      testId={namespaced('project-card-menu')}
      onRename={actions.onRename}
      onDelete={actions.onDelete}
      busy={actions.busy}
    />
  )
}

/**
 * The document-type badge, which both row renderers draw identically.
 *
 * Same reason as the menu above: the grid and the list are two renderings of one
 * row, and the wire-to-Russian mapping plus the badge's class and testid were
 * written out in both. It lives beside the menu because they are the two pieces the
 * two renderers share, and one file for "what a row shows in both shapes" is easier
 * to keep true than two.
 */
export function ProjectTypeBadge({
  documentType,
  namespaced,
}: {
  documentType: string
  namespaced: (name: string) => string
}) {
  return (
    <span
      className={projectsPageStyles['project-card-type']}
      data-testid={namespaced('project-card-type')}
    >
      {documentTypeLabelFromWire(documentType)}
    </span>
  )
}
