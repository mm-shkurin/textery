import styles from './SiteFooter.module.css'

// The product's footer — Figma `Desktop` → `Footer` (node 1362:8304) on the landing, and the
// lighter `Footer` instance the app screens place (node 788:5094, y=16279).
//
// One component for both: the landing's slab and the app screen's strip carry the same four link
// columns and the same legal line, and two components would be two places for a link to be added
// once. `variant` picks the surface, nothing else.
//
// Every link is an `<a href>` to a route that does not exist yet, which would be a lie. They are
// rendered as plain text instead, in the columns the design gives them, so the footer says what
// the product will have without promising a click it cannot honour. The support line is the one
// real address, and it is a `mailto:` that works today.
const COLUMNS = [
  { title: 'Продукт', items: ['Блог', 'Промпты'] },
  { title: 'Компания', items: ['О нас', 'Команда', 'Помощь', 'Контакты'] },
  { title: 'Решения', items: ['Школьникам', 'Студентам', 'Преподавателям', 'Консультантам'] },
  {
    title: 'Правовая информация',
    items: [
      'Юридическая информация',
      'Правила использования',
      'Политика cookie',
      'Политика конфиденциальности',
      'Условия использования',
    ],
  },
]

interface SiteFooterProps {
  // `slab` is the landing's dark closing band; `strip` is the pale rule the app screens end on.
  variant?: 'slab' | 'strip'
}

function SiteFooterBrand() {
  return (
    <div className="site-footer-brand">
      <img className={styles['site-footer-logo']} src="/design/logo-textery.svg" alt="Textery" />
      <p className={styles['site-footer-note']}>
        По всем вопросам, связанным с работой сервиса, вы можете связаться с поддержкой
      </p>
    </div>
  )
}

// The four link columns, which only the landing's slab carries — the app screens' strip is one
// rule and a legal line.
function SiteFooterColumns() {
  return (
    <nav className={styles['site-footer-columns']} aria-label="Разделы сайта">
      {COLUMNS.map((column) => (
        <div className={styles['site-footer-column']} key={column.title}>
          <h2 className={styles['site-footer-column-title']}>{column.title}</h2>
          <ul>
            {column.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  )
}

function SiteFooterLegal() {
  return (
    <div className={styles['site-footer-legal']}>
      <p>© 2026 Textery AI. Все права защищены</p>
      <p className={styles['site-footer-links']}>
        <span>Условия использования</span>
        <span>Политика конфиденциальности</span>
        <span>Поддержка</span>
      </p>
    </div>
  )
}

export function SiteFooter({ variant = 'slab' }: SiteFooterProps) {
  return (
    <footer
      className={`${styles['site-footer']} ${styles[`site-footer-${variant}`]}`}
      data-testid="site-footer"
    >
      <div className={styles['site-footer-inner']}>
        <SiteFooterBrand />
        {variant === 'slab' && <SiteFooterColumns />}
      </div>
      <SiteFooterLegal />
    </footer>
  )
}
