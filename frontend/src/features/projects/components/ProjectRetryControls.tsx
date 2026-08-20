import { useState } from 'react'
import { TEXT_STYLE_OPTIONS, type TextStyle } from '../../../shared/textStyles'

interface ProjectRetryControlsProps {
  generationId: string
  retrying: boolean
  onRetry: (generationId: string, textStyle?: TextStyle) => void
  namespaced: (testId: string) => string
}

/**
 * «Повторить» and «перегенерировать в другом стиле», as one control pair on a failed card.
 *
 * Two controls rather than one combined dropdown-button: the plain repeat is what most presses
 * are, and burying it behind a register the user has to pick first would make the common case
 * slower to serve the rare one. The select defaults to «Тот же стиль», so a user who ignores it
 * gets exactly the retry that existed before this control did.
 *
 * `''` in the select means "keep the source generation's own register" and sends no style at all —
 * distinct from picking «Научный», which overrides whatever the failed row asked for.
 */
export function ProjectRetryControls({
  generationId,
  retrying,
  onRetry,
  namespaced,
}: ProjectRetryControlsProps) {
  const [style, setStyle] = useState<TextStyle | ''>('')

  return (
    <div className="project-card-retry-row">
      <button
        type="button"
        className="project-card-retry"
        data-testid={namespaced('project-card-retry')}
        // Disabled while its own request is in flight — the guard against a double-click is
        // in the hook, but a button that stays live through the wait invites one.
        disabled={retrying}
        onClick={() => onRetry(generationId, style || undefined)}
      >
        {retrying ? 'Повторяем…' : 'Повторить'}
      </button>
      <select
        className="project-card-retry-style"
        data-testid={namespaced('project-card-retry-style')}
        // Icon-less control with no visible label: the name has to live here or it announces as
        // nothing but "combo box".
        aria-label="Стиль для повторной генерации"
        value={style}
        disabled={retrying}
        onChange={(event) => setStyle(event.target.value as TextStyle | '')}
      >
        <option value="">Тот же стиль</option>
        {TEXT_STYLE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}
