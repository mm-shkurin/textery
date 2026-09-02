interface IconProps {
  className?: string
}

// Глифы панели редактора и его верхней полосы.
//
// Панель раньше подписывала кнопки литералами из `editorToolbarActions.ts` — «B», «⌫⊞»,
// «+|», «―». Это читалось как отладочный вывод: пользователь видел набор символов, часть
// которых («⌫⊞», «+|») не значит ничего за пределами этого файла. Фрейм рисует иконки, и
// они здесь; буквенные подписи (B, I, U, S, </>) остались подписями, потому что буква и
// есть общепринятый знак для этих четырёх и для кода.
//
// Все иконки декоративные: каждая стоит внутри кнопки с собственным `aria-label`, и
// объявленная вторым голосом она назвала бы одну кнопку дважды.
function Stroke({ className, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

export function BackIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M15 5l-7 7 7 7" />
    </Stroke>
  )
}

export function DownloadIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M12 4v10m0 0 4-4m-4 4-4-4M5 19h14" />
    </Stroke>
  )
}

export function ChevronDownIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="m6 9 6 6 6-6" />
    </Stroke>
  )
}

export function CheckIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="m5 12 5 5 9-10" />
    </Stroke>
  )
}

export function BulletListIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 6h.01M4 12h.01M4 18h.01M9 6h11M9 12h11M9 18h11" />
    </Stroke>
  )
}

// Цифры внутри иконки — единственное место, где в глифе есть текст: нумерованный список
// без цифр отличается от маркированного только отсутствием точек, что на 20px не читается.
export function OrderedListIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M9 6h11M9 12h11M9 18h11" />
      <text x="2" y="8" fontSize="7" fill="currentColor" stroke="none">
        1
      </text>
      <text x="2" y="20" fontSize="7" fill="currentColor" stroke="none">
        2
      </text>
    </Stroke>
  )
}

export function QuoteIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M9 7H5v5h4v-2c0 2-1 3-3 3M19 7h-4v5h4v-2c0 2-1 3-3 3" />
    </Stroke>
  )
}

export function RuleIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 12h16" />
    </Stroke>
  )
}

export function CodeBlockIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 5h16v14H4zM9 10l-2 2 2 2M15 10l2 2-2 2" />
    </Stroke>
  )
}

export function AlignCenterIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 6h16M7 12h10M5 18h14" />
    </Stroke>
  )
}

export function TableIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 5h16v14H4zM4 10h16M10 10v9" />
    </Stroke>
  )
}

export function RowAddIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 5h16v6H4zM7 17h6M10 14v6" />
    </Stroke>
  )
}

export function ColumnAddIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 5h6v14H4zM14 8h6M17 5v6" />
    </Stroke>
  )
}

export function TableDeleteIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M4 5h16v14H4zM4 10h16M10 10v9M15 14l4 4m0-4-4 4" />
    </Stroke>
  )
}

export function LinkIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1" />
    </Stroke>
  )
}

export function UndoIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M9 8H5V4M5 8a8 8 0 1 1 3 12" />
    </Stroke>
  )
}

export function RedoIcon({ className }: IconProps) {
  return (
    <Stroke className={className}>
      <path d="M15 8h4V4m0 4a8 8 0 1 0-3 12" />
    </Stroke>
  )
}
