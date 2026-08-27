import type { FormEvent } from 'react'

import styles from './LandingHeroPrompt.module.css'

interface LandingHeroPromptProps {
  onSubmit?: () => void
}

// The topic typed here is not yet carried into the generation flow — submitting opens
// the document-type step, same as the header CTA. Wiring the topic through requires a
// change in DocumentGenerationFlow and is deliberately left for that work unit.
export function LandingHeroPrompt({ onSubmit }: LandingHeroPromptProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit?.()
  }

  return (
    <form className={styles['hero-prompt']} onSubmit={handleSubmit}>
      <input
        className={styles['hero-prompt-input']}
        type="text"
        data-testid="hero-prompt-input"
        placeholder="Опишите тему доклада, реферата, эссе, сочинения..."
        aria-label="Тема документа"
      />
      <button
        type="submit"
        className={styles['hero-prompt-button']}
        data-testid="hero-generate-button"
      >
        Сгенерировать
      </button>
    </form>
  )
}
