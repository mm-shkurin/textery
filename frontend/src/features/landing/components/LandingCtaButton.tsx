import navbarButtonsStyles from '../../../shared/components/navbar/NavbarButtons.module.css'

interface LandingCtaButtonProps {
  /** Absent means the page has no action to offer — nothing renders. */
  onClick?: () => void
  /** The section's own wrapper class: each one positions the button differently. */
  wrapperClassName: string
  testId: string
  label: string
}

/**
 * The landing's primary call to action, which four sections render identically.
 *
 * `LandingAdvantages`, `LandingComparison`, `LandingCta` and `LandingShowcase` each
 * had their own copy of the same `btn-light` button behind the same
 * `onPrimaryCtaClick !== undefined` guard, differing only in the wrapper class,
 * the testid and the label. Four copies of one button is how a restyle lands on
 * three of them.
 *
 * The guard lives HERE rather than at each call site: "no handler means no button"
 * is one rule about this control, and stating it four times is how one of them ends
 * up rendering a button that does nothing when clicked.
 */
export function LandingCtaButton({
  onClick,
  wrapperClassName,
  testId,
  label,
}: LandingCtaButtonProps) {
  if (onClick === undefined) return null
  return (
    <div className={wrapperClassName}>
      <button
        type="button"
        className={navbarButtonsStyles['btn-light']}
        data-testid={testId}
        onClick={onClick}
      >
        {label}
      </button>
    </div>
  )
}
