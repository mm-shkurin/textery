import type { ReactNode } from 'react'
import { ProfileMenu } from '../profile/ProfileMenu'
import { ThemeSwitch } from './ThemeSwitch'
import styles from './Navbar.module.css'
import './NavbarButtons.module.css'

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

// Exported from the Figma `Logo` component (node 577:2034) rather than redrawn, and one file per
// theme for every screen, so the mark cannot drift between them.
//
// TWO files, swapped in CSS, rather than one filtered: the wordmark is black and has to become
// near-white in the dark theme, but the glyph beside it is `--blue-700` and must NOT move. A CSS
// filter cannot invert one and spare the other. Both are rendered and one is hidden, so the swap
// costs no repaint and cannot flash the wrong mark between themes.
//
// `alt` on the visible one only — the hidden twin would otherwise announce the product name twice
// to a screen reader.
function NavbarLogo() {
  return (
    <>
      <img
        className={`${styles['navbar-logo']} ${styles['navbar-logo-light']}`}
        src="/design/logo-textery.svg"
        alt="Textery"
      />
      <img
        className={`${styles['navbar-logo']} ${styles['navbar-logo-dark']}`}
        src="/design/logo-textery-dark.svg"
        alt=""
      />
    </>
  )
}

// The theme switch appears only where the account menu does NOT — the menu already carries its own
// theme row, and two controls for one setting in one bar is a bug report waiting to happen. Signed
// out, the switch is the only way to reach the setting at all: the menu is behind the avatar,
// which is behind the auth gate.
function NavbarAccount({
  profileMenu,
  position,
}: Pick<NavbarProps, 'profileMenu'> & { position: 'before' | 'after' }) {
  if (profileMenu === undefined) return position === 'before' ? <ThemeSwitch /> : null
  if (position === 'before') return null
  return (
    <ProfileMenu
      onLogoutClick={profileMenu.onLogoutClick}
      testIdPrefix={profileMenu.testIdPrefix}
    />
  )
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
  const classes = [styles.navbar, styles[`navbar-${variant}`], className].filter(Boolean).join(' ')

  return (
    <Element className={classes} data-testid={testId}>
      <NavbarLogo />
      {/* The theme switch sits BEFORE the actions and the account menu AFTER them, which is the
          landing frame's order (90:880: wordmark, switch, «Вход», the blue CTA) and the signed-in
          bar's at the same time. They are two different objects that happened to share a slot:
          the switch is a setting, the menu is the account, and the design puts the setting next
          to the mark and the account at the far edge. Rendering both through one component in one
          position forced the switch to the far right on every signed-out screen. */}
      <div className={styles['navbar-actions']}>
        <NavbarAccount profileMenu={profileMenu} position="before" />
        {actions}
        <NavbarAccount profileMenu={profileMenu} position="after" />
      </div>
    </Element>
  )
}
