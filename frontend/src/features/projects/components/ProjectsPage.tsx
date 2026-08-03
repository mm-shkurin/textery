import { useEffect, useState } from 'react'
import { listProjects, type ProjectSummary } from '../api/projectsApi'
import { ProjectCard, projectKey } from './ProjectCard'
import './ProjectsPage.css'

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
        // Keyed on `projectKey`, never on id alone — see the comment on that function.
        <ProjectCard key={projectKey(project)} project={project} />
      ))}
    </div>
  )
}
