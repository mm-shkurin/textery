import authFormStyles from './AuthForm.module.css'

interface AuthSubmitButtonProps {
  testId: string
  isSubmitting: boolean
  children: React.ReactNode
}

export function AuthSubmitButton({ testId, isSubmitting, children }: AuthSubmitButtonProps) {
  return (
    <button
      type="submit"
      className={authFormStyles['auth-submit']}
      data-testid={testId}
      disabled={isSubmitting}
    >
      {children}
    </button>
  )
}
