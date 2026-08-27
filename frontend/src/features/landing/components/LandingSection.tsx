import type { ReactNode } from 'react'
import landingSectionStyles from './LandingSection.module.css'

interface LandingSectionProps {
  testId: string
  /**
   * The section's own class, ADDED to the shared one, never replacing it — the same
   * rule `LandingSectionHead` uses for its overrides, so a section cannot quietly
   * drop out of the shared shell while still appearing to use it.
   */
  className?: string
  children: ReactNode
}

/**
 * The `<section>` shell every landing block opens with.
 *
 * `LandingSectionHead` already owns the eyebrow/title/lead inside it; this owns the
 * element around it, which five components had written out by hand. Together they
 * mean a section is its content, and the shell it sits in is stated once.
 *
 * Five, not six: `LandingComparison` puts the same class on an inner `<div>` rather
 * than on its `<section>`, because the dark band bleeds full-width while its content
 * stays in the column. That is a different element doing a different job, and forcing
 * it through here would mean an `as` prop — a shell that renders anything is not a
 * shell.
 */
export function LandingSection({ testId, className, children }: LandingSectionProps) {
  const shell = landingSectionStyles['landing-section']
  return (
    <section className={className ? `${shell} ${className}` : shell} data-testid={testId}>
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
