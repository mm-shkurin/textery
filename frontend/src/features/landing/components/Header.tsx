import './Header.css'

interface HeaderProps {
  onPrimaryCtaClick?: () => void
}

export function Header({ onPrimaryCtaClick }: HeaderProps) {
  return (
    <header className="site-header">
      <img className="brand-logo" src="/logo.svg" alt="Textery" />
      <div className="header-actions">
        <button
          type="button"
          className="btn-light"
          data-testid="header-primary-cta-button"
          onClick={onPrimaryCtaClick}
        >
          Создать генерацию
        </button>
      </div>
    </header>
  )
}
