import { useEffect, useState } from 'react'
import { listProjects, type ProjectSummary } from '../api/projectsApi'
import { ProjectCard } from './ProjectCard'

// The «Мои проекты» feed. Scenario 1.1 only: the cards, and nothing around them — no search, no
// sort, no view toggle, no paging control. Those arrive with their own scenarios and their own
// tests; adding the markup now would ship controls that answer to nothing.
export function ProjectsPage() {
  const [items, setItems] = useState<ProjectSummary[]>([])

  useEffect(() => {
    let cancelled = false
    listProjects().then((page) => {
      // The component unmounts mid-flight in a test teardown and in every route change; setting
      // state on the way out is a warning today and a leak the moment paging keeps a second
      // request alive.
      if (!cancelled) setItems(page.items)
    })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="projects-page" data-testid="projects-page">
      {items.map((project) => (
        // Keyed on (kind, id), never on id alone: the two arms of the feed come from different
        // tables and their ids CAN collide, which would collapse a document and a generation onto
        // one node.
        <ProjectCard key={`${project.kind}-${project.id}`} project={project} />
      ))}
    </div>
  )
}
