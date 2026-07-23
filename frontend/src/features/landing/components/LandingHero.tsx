import type { FormEvent } from 'react'

import './LandingHero.css'

interface LandingHeroProps {
  onPromptSubmit?: () => void
}

// Figma `Desktop` (node 90:880): the hero is a two-line 44px heading whose second line is
// split — "нейросеть" stays near-black, "для докладов" is brand blue.
export function LandingHero({ onPromptSubmit }: LandingHeroProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onPromptSubmit?.()
  }

  return (
    <section className="hero">
      <div className="hero-glass hero-glass-left" aria-hidden="true">
        <img src="/design/glass-16.png" alt="" />
        <img src="/design/glass-8.png" alt="" />
      </div>
      <div className="hero-glass hero-glass-right" aria-hidden="true">
        <img src="/design/glass-24.png" alt="" />
        <img src="/design/glass-9.png" alt="" />
      </div>

      <h1 className="hero-title" data-testid="hero-heading">
        Textery — самая быстрая <span className="hero-title-accent">нейросеть для докладов</span>
      </h1>

      <p className="hero-subtitle">
        Создавайте <strong>профессиональные доклады, как в Worde</strong>, с помощью искусственного
        интеллекта. Генерация докладов <strong>за 30 секунд</strong>
      </p>

      {/* The topic typed here is not yet carried into the generation flow — submitting opens
          the document-type step, same as the header CTA. Wiring the topic through requires a
          change in DocumentGenerationFlow and is deliberately left for that work unit. */}
      <form className="hero-prompt" onSubmit={handleSubmit}>
        <input
          className="hero-prompt-input"
          type="text"
          data-testid="hero-prompt-input"
          placeholder="Опишите тему доклада, реферата, эссе, сочинения..."
          aria-label="Тема документа"
        />
        <button type="submit" className="hero-prompt-button" data-testid="hero-generate-button">
          Сгенерировать
        </button>
      </form>
    </section>
  )
}
