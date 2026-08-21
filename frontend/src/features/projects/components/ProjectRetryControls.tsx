import { useState } from 'react'
import { TEXT_STYLE_OPTIONS, type TextStyle } from '../../../shared/domain/textStyles'
import { VOLUME_PAGE_OPTIONS } from '../../../shared/domain/volumePages'
import type { RetryOverrides } from '../api/retryGenerationApi'
import projectCardStyles from './ProjectCard.module.css'

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
    <div className={projectCardStyles['project-card-retry-row']}>
      <button
        type="button"
        className={projectCardStyles['project-card-retry']}
        data-testid={namespaced('project-card-retry')}
        // Disabled while its own request is in flight — the guard against a double-click is
        // in the hook, but a button that stays live through the wait invites one.
        disabled={retrying}
        onClick={() => onRetry(generationId, overrides())}
      >
        {retrying ? 'Повторяем…' : 'Повторить'}
      </button>
      <RetryChoice
        testId={namespaced('project-card-retry-style')}
        label="Стиль для повторной генерации"
        unchanged="Тот же стиль"
        value={style}
        disabled={retrying}
        onChange={(next) => setStyle(next as TextStyle | '')}
        options={TEXT_STYLE_OPTIONS.map((option) => ({ value: option.value, label: option.label }))}
      />
      {/* A select, not the composer's number input. The retry needs a real "unchanged" state, and
          an emptied number input reports NaN — the exact trap the composer documents. Enumerating
          the allowed lengths also means this control cannot produce a value the server refuses. */}
      <RetryChoice
        testId={namespaced('project-card-retry-volume')}
        label="Объём для повторной генерации"
        unchanged="Тот же объём"
        value={volume}
        disabled={retrying}
        onChange={setVolume}
        options={VOLUME_PAGE_OPTIONS.map((pages) => ({
          value: String(pages),
          label: `${pages} стр.`,
        }))}
      />
    </div>
  )
}

interface RetryChoiceProps {
  testId: string
  label: string
  // What the empty value reads as. `''` means "keep what the failed run used", which is a real
  // choice and not a prompt to be dismissed — so it is an option with words, not a placeholder.
  unchanged: string
  value: string
  disabled: boolean
  onChange: (value: string) => void
  options: readonly { value: string; label: string }[]
}

// The two pickers differ only in their words and their list. Written out twice they were the
// longest thing in this file and the easiest place for the pair to drift — one of them losing its
// `aria-label`, or staying live while a retry is in flight.
function RetryChoice({
  testId,
  label,
  unchanged,
  value,
  disabled,
  onChange,
  options,
}: RetryChoiceProps) {
  return (
    <select
      className={projectCardStyles['project-card-retry-select']}
      data-testid={testId}
      // Icon-less control with no visible label: the name has to live here or it announces as
      // nothing but "combo box".
      aria-label={label}
      value={value}
      disabled={disabled}
      onChange={(event) => onChange(event.target.value)}
    >
      <option value="">{unchanged}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}
