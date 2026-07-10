interface PlaceholderImageProps {
  className?: string
}

export function PlaceholderImage({ className }: PlaceholderImageProps) {
  return (
    <svg
      className={className}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <rect x="1" y="1" width="98" height="98" rx="10" stroke="currentColor" strokeWidth="2" />
      <circle cx="66" cy="34" r="9" stroke="currentColor" strokeWidth="2" />
      <path d="M1 72 L34 44 L60 66 L99 34" stroke="currentColor" strokeWidth="2" />
    </svg>
  )
}
