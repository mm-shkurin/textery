import { useState } from 'react'
import styles from './LandingExamples.module.css'
import landingSectionStyles from './LandingSection.module.css'
import navbarButtonsStyles from '../../../shared/components/navbar/NavbarButtons.module.css'
import { LANDING_EXAMPLES, type LandingExample } from '../utils/landingExamples'

interface LandingExamplesProps {
  onPrimaryCtaClick?: () => void
}

/**
 * «Посмотреть примеры готовых работ» — the section a visitor reads before deciding to sign up.
 *
 * The landing argued for the product in the abstract — advantages, a comparison, a FAQ — and
 * never showed a single line of what it produces. This section is the output itself: four real
 * openings, one per type, each expandable to the full excerpt.
 *
 * Expansion is native `<details>`, not a modal: the summary IS the clickable control, keyboard
 * operation and the open/closed announcement come with the element, and the closed card still
 * renders its text in the DOM — so a visitor who searches the page with ctrl-F finds what is
 * inside a card they have not opened.
 *
 * `open` is driven ENTIRELY from React state, and the summary's own click is prevented. Letting
 * the element toggle itself and listening for `toggle` looks simpler and is not: `toggle` is
 * queued as a task rather than dispatched synchronously, so between the element opening itself and
 * the component hearing about it the DOM and React's `open` prop disagree — and one card can end
 * up open in the DOM while React believes it closed. Prevent-and-drive keeps a single source of
 * truth for which card is open, which is what the accordion rule needs.
 */
export function LandingExamples({ onPrimaryCtaClick }: LandingExamplesProps) {
  // Which card is open, so the group behaves as an accordion: four cards expanded at once turn
  // this section into a wall of body text, and the point is a sample, not the whole document.
  const [openId, setOpenId] = useState<LandingExample['id'] | null>(LANDING_EXAMPLES[0].id)

  return (
    <section className={landingSectionStyles['landing-section']} data-testid="landing-examples">
      <div className={landingSectionStyles['landing-section-head']}>
        <span className={landingSectionStyles['landing-eyebrow']}>Примеры</span>
        <h2 className={landingSectionStyles['landing-section-title']}>Примеры готовых работ</h2>
        <p className={landingSectionStyles['landing-section-lead']}>
          Так выглядит результат: тема, объём и первые абзацы текста, который вы получите
        </p>
      </div>

      <div className={`${landingSectionStyles['landing-section-body']} ${styles['examples-grid']}`}>
        {LANDING_EXAMPLES.map((example) => (
          <details
            key={example.id}
            className={styles['example-card']}
            data-testid="landing-example"
            open={openId === example.id}
          >
            <summary
              className={styles['example-summary']}
              // Prevented so the element does not also toggle itself — see the note above. The
              // handler sits on the summary rather than the details so keyboard activation
              // (Enter/Space on the focused summary, which dispatches a click) goes through the
              // same path as a mouse press.
              onClick={(event) => {
                event.preventDefault()
                setOpenId(openId === example.id ? null : example.id)
              }}
            >
              <span className={styles['example-chip']}>{example.typeLabel}</span>
              <span className={styles['example-title']}>{example.title}</span>
              <span className={styles['example-volume']}>{example.volume}</span>
            </summary>
            <p className={styles['example-excerpt']}>{example.excerpt}</p>
          </details>
        ))}
      </div>

      <div className={styles['examples-action']}>
        <button
          type="button"
          className={navbarButtonsStyles['btn-light']}
          data-testid="examples-primary-cta-button"
          onClick={onPrimaryCtaClick}
        >
          Создать свою работу
        </button>
      </div>
    </section>
  )
}
