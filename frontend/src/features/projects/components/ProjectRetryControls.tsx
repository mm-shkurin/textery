import { useState } from 'react'
import { TEXT_STYLE_OPTIONS, type TextStyle } from '../../../shared/textStyles'
import { VOLUME_PAGE_OPTIONS } from '../../../shared/volumePages'
import type { RetryOverrides } from '../api/retryGenerationApi'

interface ProjectRetryControlsProps {
  generationId: string
  retrying: boolean
  onRetry: (generationId: string, overrides?: RetryOverrides) => void
  namespaced: (testId: string) => string
}

/**
 * «Повторить», plus the two things a user may re-choose while doing it: the register
 * («перегенерировать в другом стиле») and the length («изменить объём»).
 *
 * Separate controls rather than one combined dropdown-button: the plain repeat is what most
 * presses are, and burying it behind choices the user has to make first would make the common
 * case slower to serve the rare one. Both pickers default to «то же самое», so a user who ignores
 * them gets exactly the retry that existed before these controls did.
 *
 * `''` in either select means "keep what the failed run used" and sends that field not at all —
 * distinct from picking a value, which overrides whatever the source row held.
 */
export function ProjectRetryControls({
  generationId,
  retrying,
  onRetry,
  namespaced,
}: ProjectRetryControlsProps) {
  const [style, setStyle] = useState<TextStyle | ''>('')
  const [volume, setVolume] = useState<string>('')

  // Built here rather than in the handler so the "empty means omit" rule is written once, next to
  // the two pieces of state it reads. Undefined, never null: the API client omits an undefined
  // field, while a null would be sent and read by the server as "clear this".
  const overrides = (): RetryOverrides | undefined => {
    const chosen: RetryOverrides = {}
    if (style) chosen.textStyle = style
    if (volume) chosen.volumePages = Number(volume)
    return Object.keys(chosen).length > 0 ? chosen : undefined
  }

  return (
    <div className="project-card-retry-row">
      <button
        type="button"
        className="project-card-retry"
        data-testid={namespaced('project-card-retry')}
        // Disabled while its own request is in flight — the guard against a double-click is
        // in the hook, but a button that stays live through the wait invites one.
        disabled={retrying}
        onClick={() => onRetry(generationId, overrides())}
      >
        {retrying ? 'Повторяем…' : 'Повторить'}
      </button>
      <select
        className="project-card-retry-select"
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
      {/* A select, not the composer's number input. The retry needs a real "unchanged" state, and
          an emptied number input reports NaN — the exact trap the composer documents. Enumerating
          the allowed lengths also means this control cannot produce a value the server refuses. */}
      <select
        className="project-card-retry-select"
        data-testid={namespaced('project-card-retry-volume')}
        aria-label="Объём для повторной генерации"
        value={volume}
        disabled={retrying}
        onChange={(event) => setVolume(event.target.value)}
      >
        <option value="">Тот же объём</option>
        {VOLUME_PAGE_OPTIONS.map((pages) => (
          <option key={pages} value={String(pages)}>
            {pages} стр.
          </option>
        ))}
      </select>
    </div>
  )
}
