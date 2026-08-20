import { useEffect, useRef } from 'react'
import type { Profile } from '../../../shared/identity/api/profileApi'
import {
  DELETION_CONFIRM_TITLE,
  DELETION_CONSEQUENCE,
  DELETION_PASSWORD_HINT,
  deletionEmailHint,
} from '../utils/profileCopy'
import type { AccountDeletion } from '../hooks/useAccountDeletion'
import { listenToDocument } from '../../../shared/lib/browser'
import profileModalStyles from './ProfileModal.module.css'
import profileButtonsStyles from './ProfileButtons.module.css'

interface ProfileDeleteModalProps {
  profile: Profile
  deletion: AccountDeletion
}

// Figma node 1202:6227 — the 624×250 panel centred over a blurred page.
//
// It carries ONE thing the design does not draw: the confirmation field. The mockup's modal is a
// title, a sentence and two buttons, which would make «Удалить навсегда» a single click away from
// an account and everything in it. The typed confirmation is a tested contract, not decoration, so
// the panel grows taller than the mockup rather than the guard being dropped to fit it.
export function ProfileDeleteModal({ profile, deletion }: ProfileDeleteModalProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  // A modal that opened with focus still on the page behind it leaves a keyboard user tabbing
  // through the form they just left to reach the dialog that is covering it.
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      // Escape is the way out of every dialog on the platform, and this one must not be the
      // exception that traps somebody in front of an irreversible button. Ignored mid-request:
      // the DELETE is already gone, and closing would hide its answer.
      if (event.key === 'Escape' && !deletion.busy) deletion.cancel()
    }
    return listenToDocument('keydown', onKeyDown)
  }, [deletion])

  return (
    <div className={profileModalStyles['profile-modal-scrim']}>
      <dialog
        className={profileModalStyles['profile-modal']}
        open
        aria-modal="true"
        aria-labelledby="profile-delete-title"
        data-testid="account-delete-confirm"
      >
        <h3 className={profileModalStyles['profile-modal-title']} id="profile-delete-title">
          {DELETION_CONFIRM_TITLE}
        </h3>
        {/* What is lost, before what to type. The frame puts this sentence under the title and
            the product had only ever shown the instruction — so the irreversible half of an
            irreversible dialog was the half missing from it. */}
        <p className={profileModalStyles['profile-modal-warning']}>{DELETION_CONSEQUENCE}</p>
        <p className={profileModalStyles['profile-modal-hint']}>
          {deletion.kind === 'password' ? DELETION_PASSWORD_HINT : deletionEmailHint(profile.email)}
        </p>

        {/* One field, and WHICH field is the account's decision, not the screen's. An account that
            signed up through Yandex has no password to type; asking for one would be a door with
            no key. */}
        <input
          ref={inputRef}
          className={profileModalStyles['profile-modal-input']}
          data-testid={
            deletion.kind === 'password' ? 'deletion-password-input' : 'deletion-email-input'
          }
          type={deletion.kind === 'password' ? 'password' : 'email'}
          autoComplete={deletion.kind === 'password' ? 'current-password' : 'off'}
          aria-label={deletion.kind === 'password' ? 'Пароль' : 'Адрес аккаунта'}
          placeholder={deletion.kind === 'password' ? 'Пароль' : profile.email}
          value={deletion.value}
          disabled={deletion.busy}
          onChange={(event) => deletion.setValue(event.target.value)}
        />

        {deletion.error !== null && (
          <p
            className={profileModalStyles['profile-modal-error']}
            role="alert"
            data-testid="deletion-error"
          >
            {deletion.error}
          </p>
        )}

        <div className={profileModalStyles['profile-modal-actions']}>
          {/* Cancel first in the DOM and visually left of the destructive one: the way out is the
              more likely intention of somebody who has got this far and paused. */}
          <button
            type="button"
            className={profileButtonsStyles['profile-btn-ghost']}
            data-testid="deletion-cancel-button"
            disabled={deletion.busy}
            onClick={deletion.cancel}
          >
            Отмена
          </button>
          <button
            type="button"
            className={profileButtonsStyles['profile-btn-danger']}
            data-testid="deletion-confirm-button"
            // Disabled until the confirmation actually matches. For the address that means an
            // exact match — the gesture is proving you know which account this is, and a near-miss
            // proves nothing.
            disabled={!deletion.confirmed || deletion.busy}
            onClick={() => void deletion.confirm()}
          >
            {deletion.busy ? 'Удаляем…' : 'Удалить аккаунт'}
          </button>
        </div>
      </dialog>
    </div>
  )
}
