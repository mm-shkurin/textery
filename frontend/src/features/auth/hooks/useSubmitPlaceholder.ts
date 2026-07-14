import { useState } from 'react'

const SUBMIT_PLACEHOLDER_DELAY_MS = 500

/**
 * Placeholder in-flight boundary — no login/registration API exists yet
 * (backend endpoints are being built in a parallel session). A real delay is
 * used instead of Promise.resolve() so the disabled window is long enough
 * for Selenium to observe it in a real browser.
 */
export function useSubmitPlaceholder() {
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submitWithPlaceholderDelay(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isSubmitting) return
    setIsSubmitting(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, SUBMIT_PLACEHOLDER_DELAY_MS))
    } finally {
      setIsSubmitting(false)
    }
  }

  return { isSubmitting, handleSubmit: submitWithPlaceholderDelay }
}
