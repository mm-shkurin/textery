import { Navbar } from '../../../shared/components/navbar/Navbar'
import navbarPlacementStyles from '../../../shared/components/navbar/NavbarPlacement.module.css'

interface ProjectsNavbarProps {
  onLogoutClick?: () => void
}

// «Мои проекты» top bar. It is now the shared `Navbar` in its `pill` shell — the design draws one
// bar for the product (Figma `Navbar/Variant5`, node 1086:4929), and the earlier note here arguing
// that this pill and the workspace bar were different objects described the drift, not the design.
// What stays local is only where the pill sits on this page.
//
// The design's notification bell is left out: there is no notifications endpoint and no unread
// count to drive it, so it could only ever be a button that does nothing under a dot that always
// glows. It belongs to the story that builds notifications.
export function ProjectsNavbar({ onLogoutClick }: ProjectsNavbarProps) {
  // The air under the bar lives on a transparent wrapper, not on the bar: padding on the pill
  // would grow the white plate, and a bottom margin can collapse out through a parent that has no
  // padding or border — the same way the profile screen's top gap became a blue band.
  return (
    <div className={navbarPlacementStyles['navbar-projects-placement']}>
      <Navbar
        as="nav"
        variant="pill"
        testId="projects-navbar"
        // Фрейм рисует тумблер темы рядом с аватаром — на этом экране он есть у
        // авторизованного пользователя, а не только у гостя.
        themeSwitch
        profileMenu={
          onLogoutClick === undefined ? undefined : { onLogoutClick, testIdPrefix: 'projects' }
        }
      />
    </div>
  )
}
