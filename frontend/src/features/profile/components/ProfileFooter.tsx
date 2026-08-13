// The footer every profile mockup draws. Its three labels are TEXT, not links: the app has no
// terms, privacy or support page, and an <a href="#"> would be a control that does nothing —
// worse than a label, because it invites the click.
export function ProfileFooter() {
  return (
    <footer className="profile-footer">
      <img className="profile-navbar-logo" src="/design/logo-textery.svg" alt="Textery" />
      <span>© 2026 Textery. Все права защищены.</span>
      <span className="profile-footer-links">
        <span>Условия использования</span>
        <span>Политика конфиденциальности</span>
        <span>Поддержка</span>
      </span>
    </footer>
  )
}
