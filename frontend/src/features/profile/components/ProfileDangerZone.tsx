import type { Profile } from '../../../shared/identity/api/profileApi'
import {
  DELETION_CONFIRM_TITLE,
  DELETION_PASSWORD_HINT,
  DELETION_TITLE,
  DELETION_WARNING,
  deletionEmailHint,
} from '../profileCopy'
import { useAccountDeletion } from '../useAccountDeletion'
import './ProfileDangerZone.css'

interface ProfileDangerZoneProps {
  profile: Profile
}

// The only irreversible thing in the product, in its own block at the bottom of the screen.
//
// Two properties have to hold at once, and they pull against each other: it must be impossible to
// do by accident, and it must be possible to do on purpose. So the button opens a confirmation
// and never deletes anything itself — and the confirmation asks for one specific thing the user
// knows (their password, or their own address), not a checkbox and not a second «вы уверены?»,
// which people click through without reading.
//
// It sits BELOW the card rather than inside it, with its own frame: everything above is a setting
// that can be changed back, and this cannot. The frame is drawn with the error tokens rather than
// a red literal — it must stay legible in the dark theme, where a hardcoded red on a hardcoded
// pale background is an unreadable stripe.
export function ProfileDangerZone({ profile }: ProfileDangerZoneProps) {
  const deletion = useAccountDeletion(profile)

  return (
    <section className="profile-danger" data-testid="profile-danger-zone">
      <h2 className="profile-danger-title">{DELETION_TITLE}</h2>
      <p className="profile-danger-warning">{DELETION_WARNING}</p>

      {!deletion.open ? (
        <button
          type="button"
          className="profile-danger-button"
          data-testid="account-delete-button"
          onClick={deletion.openConfirmation}
        >
          Удалить аккаунт
        </button>
      ) : (
        <div className="profile-danger-confirm" data-testid="account-delete-confirm">
          <h3 className="profile-danger-confirm-title">{DELETION_CONFIRM_TITLE}</h3>
          <p className="profile-danger-hint">
            {deletion.kind === 'password'
              ? DELETION_PASSWORD_HINT
              : deletionEmailHint(profile.email)}
          </p>

          {/* One field, and WHICH field is the account's decision, not the screen's. An account
              that signed up through Yandex has no password to type; asking for one would be a
              door with no key. */}
          <input
            className="profile-danger-input"
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
            <p className="profile-danger-error" role="alert" data-testid="deletion-error">
              {deletion.error}
            </p>
          )}

          <div className="profile-danger-actions">
            {/* Cancel first in the DOM and visually left of the destructive one: the way out is
                the more likely intention of somebody who has got this far and paused. */}
            <button
              type="button"
              className="profile-danger-cancel"
              data-testid="deletion-cancel-button"
              disabled={deletion.busy}
              onClick={deletion.cancel}
            >
              Отмена
            </button>
            <button
              type="button"
              className="profile-danger-button"
              data-testid="deletion-confirm-button"
              // Disabled until the confirmation actually matches. For the address that means an
              // exact match — the gesture is proving you know which account this is, and a
              // near-miss proves nothing.
              disabled={!deletion.confirmed || deletion.busy}
              onClick={() => void deletion.confirm()}
            >
              {deletion.busy ? 'Удаляем…' : 'Удалить навсегда'}
            </button>
          </div>
        </div>
      )}
    </section>
  )
}
