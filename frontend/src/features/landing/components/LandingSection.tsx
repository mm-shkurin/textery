import type { ReactNode } from 'react'
import landingSectionStyles from './LandingSection.module.css'

interface LandingSectionProps {
  testId: string
  children: ReactNode
}

/**
 * The `<section>` shell every landing block opens with.
 *
 * `LandingSectionHead` already owns the eyebrow/title/lead inside it; this owns the
 * element around it, which six components had also written out by hand. Together
 * they mean a section is its content, and the shell it sits in is stated once.
 */
export function LandingSection({ testId, children }: LandingSectionProps) {
  return (
    <section className={landingSectionStyles['landing-section']} data-testid={testId}>
      {children}
    </section>
  )
}

/**
 * The accented first line of a section title.
 *
 * Four titles open with the same `<span>` carrying the accent class and differ only
 * in what follows it, so the span is the shared part and the rest stays at the call
 * site where the copy lives.
 */
export function AccentLine({ children }: { children: ReactNode }) {
  return <span className={landingSectionStyles['landing-section-title-accent']}>{children}</span>
}
