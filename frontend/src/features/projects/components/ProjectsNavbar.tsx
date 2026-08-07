import { ProfileMenu } from '../../../shared/components/profile/ProfileMenu'
import './ProjectsNavbar.css'

interface ProjectsNavbarProps {
  onLogoutClick?: () => void
}

// «Мои проекты» draws its own top bar — Figma `Navbar` as instanced in the frame «Мои проекты -
// после авторизации (нет проектов)» (node 573:4518). It is NOT the `AppHeader` used by the
// workspace and the editor: that one is a full-width bar with a bottom rule, this one is a white
// pill floating on the page background with the logo at one end and the account at the other.
// Sharing a component between the two would mean a component whose every rule is behind a flag.
//
// The design's notification bell is left out: there is no notifications endpoint and no unread
// count to drive it, so it could only ever be a button that does nothing under a dot that always
// glows. It belongs to the story that builds notifications.
export function ProjectsNavbar({ onLogoutClick }: ProjectsNavbarProps) {
  return (
    <nav className="projects-navbar" data-testid="projects-navbar">
      {/* Exported from the Figma `Logo` component rather than redrawn, and the same asset the
          landing header uses — one file, so the mark cannot drift between screens. */}
      <img className="projects-navbar-logo" src="/design/logo-textery.svg" alt="Textery" />
      {onLogoutClick !== undefined && (
        <ProfileMenu onLogoutClick={onLogoutClick} testIdPrefix="projects" />
      )}
    </nav>
  )
}
