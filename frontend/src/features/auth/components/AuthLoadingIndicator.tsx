interface AuthLoadingIndicatorProps {
  testId: string
}

export function AuthLoadingIndicator({ testId }: AuthLoadingIndicatorProps) {
  return (
    <div className="auth-loading-indicator" data-testid={testId} role="status" aria-live="polite">
      Загрузка...
    </div>
  )
}
