import { PlaceholderImage } from '../../../shared/components/PlaceholderImage'
import manualEditorStyles from './ManualEditor.module.css'

interface ManualEditorErrorBannerProps {
  // Which failure this banner speaks for — the two callers say different things (an init failure
  // means "this editor cannot persist", a save failure means "this attempt failed, try again"), so
  // each keeps its own testid and message while the markup is stated once.
  testId: string
  message: string
}

// Pure presentation, extracted from ManualEditor where the same alert markup was spelled twice —
// once for initError and once for saveError, differing only in the two props above. `role="alert"`
// is what makes either failure reach assistive tech without focus moving, so it belongs to the
// shape rather than to a caller.
//
// Styling stays in ManualEditor.css (`.me-error-banner`, `.me-error-banner-icon`): this renders
// inside that shell, which already imports it, and splitting two rules into a third stylesheet
// would buy nothing.
export function ManualEditorErrorBanner({ testId, message }: ManualEditorErrorBannerProps) {
  return (
    <div className={manualEditorStyles['me-error-banner']} role="alert" data-testid={testId}>
      <PlaceholderImage className={manualEditorStyles['me-error-banner-icon']} />
      {message}
    </div>
  )
}
