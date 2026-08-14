import type { ReactNode } from 'react'
import { ProfileMenu } from '../profile/ProfileMenu'
import './Navbar.css'
import './NavbarButtons.css'

// The one top bar. Figma `Navbar/Variant5` (COMPONENT, node 1086:4929) — the design draws a single
// bar for every authenticated screen, and the product had grown four: the landing header, the
// «Мои проекты» pill, the profile pill, and the workspace bar. Four files meant four places for a
// padding value to drift, and they had already drifted (72/88px pill vs 20px flat bar).
//
// The four names survive as thin wrappers around this component rather than being deleted at the
// call sites. That is deliberate: `AppHeader` is imported by the generation screens and
// `ProjectsNavbar`/`ProfileHeader` by their pages, all of which are other people's files this
// session must not touch. A wrapper keeps every import and every `data-testid` exactly where it
// was while the markup underneath becomes one thing.
//
// `variant` is the SHELL the bar sits in, not a licence to restyle it: `pill` floats on the page
// background (projects, profile), `flat` sits directly on it with no surface (landing), `bar` is
// full-width with a bottom rule (workspace). Everything inside — logo size, action buttons, the
// account menu — is identical across all three.
export type NavbarVariant = 'flat' | 'pill' | 'bar'

interface NavbarProps {
  variant: NavbarVariant
  // `nav` for the projects bar, which is a landmark of its own; `header` everywhere else.
  as?: 'header' | 'nav'
  className?: string
  testId?: string
  // The action buttons left of the account, in render order. Passed as nodes rather than a
  // descriptor list because each caller owns its own labels, testids and handlers, and a
  // descriptor type would have to grow a field every time one of them needed something new.
  actions?: ReactNode
  // Rendered only when the caller asks for it. Each screen decides differently (the landing shows
  // it only to a signed-in visitor, the profile screen unconditionally), so the decision stays
  // with the caller and this component just obeys.
  profileMenu?: { onLogoutClick: () => void; testIdPrefix: string }
}

export function Navbar({
  variant,
  as = 'header',
  className,
  testId,
  actions,
  profileMenu,
}: NavbarProps) {
  const Element = as
  const classes = ['navbar', `navbar-${variant}`, className].filter(Boolean).join(' ')

  return (
    <Element className={classes} data-testid={testId}>
      {/* Exported from the Figma `Logo` component (node 577:2034) rather than redrawn, and one
          file for every screen, so the mark cannot drift between them. */}
      <img className="navbar-logo" src="/design/logo-textery.svg" alt="Textery" />
      <div className="navbar-actions">
        {actions}
        {profileMenu !== undefined && (
          <ProfileMenu
            onLogoutClick={profileMenu.onLogoutClick}
            testIdPrefix={profileMenu.testIdPrefix}
          />
        )}
      </div>
    </Element>
  )
}
