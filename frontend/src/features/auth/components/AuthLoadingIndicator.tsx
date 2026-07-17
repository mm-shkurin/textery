interface AuthLoadingIndicatorProps {
  testId: string
}

// <output>, not a div with role="status": the element carries that role implicitly, so the
// markup states the semantics instead of annotating them onto a generic box. aria-live stays
// explicit — `polite` is <output>'s default, but this text exists ONLY to be announced, and
// leaving the one property it depends on to a default is how it quietly stops being announced.
export function AuthLoadingIndicator({ testId }: AuthLoadingIndicatorProps) {
  return (
    <output className="auth-loading-indicator" data-testid={testId} aria-live="polite">
      Загрузка...
    </output>
  )
}
