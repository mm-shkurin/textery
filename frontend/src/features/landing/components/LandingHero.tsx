import type { FormEvent } from 'react'

import styles from './LandingHero.module.css'

interface LandingHeroProps {
  onPromptSubmit?: () => void
}

// Figma `Desktop` (node 90:880): the hero is a two-line 44/53 heading whose second line is brand
// blue. The words are the frame's: «нейросеть для учебных текстов», not «для докладов» — the
// product makes four kinds of text and naming one of them in the first line of the page reads as
// a limit on what it can do.
export function LandingHero({ onPromptSubmit }: LandingHeroProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onPromptSubmit?.()
  }

  return (
    <section className={styles.hero}>
      {/* The faint 60px grid the frame lays under the hero, fading out toward the edges. Drawn in
          CSS rather than shipped as artwork: it is two repeating gradients and a mask, and an
          image of it would be another request on the first screen. */}
      <div className={styles['hero-grid']} aria-hidden="true" />
      {/* Decorative only (aria-hidden), and they used to cost 6.5 MB of PNG — more than the rest
          of the page put together, on the one screen a first-time visitor sees before anything
          else. Re-encoded to WebP at twice the CSS box each one actually renders at (798, 714,
          732, 738 px wide respectively), for 0.84 MB total. Keep any replacement in that budget:
          an ornament that delays the heading is worse than no ornament.

          The renders themselves are the ones embedded in the design frame, not the versions that
          shipped first: those were a washed-out, near-white variant of the same four shapes, and
          on the pale blue page they read as smudges rather than glass. */}
      <div className={`${styles['hero-glass']} ${styles['hero-glass-left']}`} aria-hidden="true">
        <img src="/design/glass-16.webp" alt="" decoding="async" />
        <img src="/design/glass-8.webp" alt="" decoding="async" />
      </div>
      <div className={`${styles['hero-glass']} ${styles['hero-glass-right']}`} aria-hidden="true">
        <img src="/design/glass-24.webp" alt="" decoding="async" />
        <img src="/design/glass-9.webp" alt="" decoding="async" />
      </div>

      {/* The frame breaks the heading after «быстрая» and paints only the closing three words
          blue — «нейросеть» stays in the ink colour. Painting the whole second line blue, as this
          did, moved the emphasis from what the product is FOR onto the word «нейросеть», which
          every competitor also says. */}
      <h1 className={styles['hero-title']} data-testid="hero-heading">
        Textery — самая быстрая <br />
        нейросеть <span className={styles['hero-title-accent']}>для учебных текстов</span>
      </h1>

      <p className={styles['hero-subtitle']}>
        Создавайте <strong>профессиональные доклады, как в Word</strong>, с помощью искусственного
        интеллекта. Генерация докладов <strong>за 30 секунд</strong>
      </p>

      {/* The topic typed here is not yet carried into the generation flow — submitting opens
          the document-type step, same as the header CTA. Wiring the topic through requires a
          change in DocumentGenerationFlow and is deliberately left for that work unit. */}
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
    </section>
  )
}
