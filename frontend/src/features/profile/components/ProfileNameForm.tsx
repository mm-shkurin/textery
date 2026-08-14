import type { Profile } from '../../../shared/identity/api/profileApi'
import { NAME_MAX_CODE_POINTS } from '../../../shared/identity/nameValue'
import { SAVE_FAILED_MESSAGE } from '../profileCopy'
import { useProfileNameForm } from '../useProfileNameForm'

interface ProfileNameFormProps {
  profile: Profile
  markDirty: () => void
  markClean: () => void
}

// The card's bottom half: set or clear the display name (mockups 02–05, plus the ninth state the
// mockups do not draw — a save that never reached the server).
export function ProfileNameForm({ profile, markDirty, markClean }: ProfileNameFormProps) {
  const form = useProfileNameForm(profile, { markDirty, markClean })

  return (
    <form
      className="profile-form"
      onSubmit={(event) => {
        // Enter in the field submits, and the browser would reload the page doing it. The same
        // handler as the button, so a second Enter hits the same one-PATCH guard a second click
        // does.
        event.preventDefault()
        void form.save()
      }}
    >
      {/* The state with no mockup: the save left, nothing came back. A BANNER above the filled-in
          card rather than an inline field error — the field is not what is wrong. The typed value
          is kept, the form stays usable, and «Повторить» is the same save again. */}
      {form.saveFailed && (
        <div className="profile-save-failed" role="alert" data-testid="profile-save-failed">
          <span>{SAVE_FAILED_MESSAGE}</span>
          <button type="button" className="profile-btn-ghost" onClick={() => void form.save()}>
            Повторить
          </button>
        </div>
      )}

      {/* No «Отображаемое имя» heading over the field any more: the design's row is labelled «Имя»
          and the card it sits in is already titled «Личные данные». Two headings and a label for
          one text input is three names for the same thing. */}
      <div className="profile-field">
        <div className="profile-label-row">
          <label className="profile-label" htmlFor="profile-name-input">
            Имя
          </label>
          <span
            className={`profile-counter${form.overLength ? ' profile-counter-over' : ''}`}
            data-testid="profile-name-counter"
          >
            {form.count} / {NAME_MAX_CODE_POINTS}
          </span>
        </div>
        <input
          id="profile-name-input"
          className={`profile-input${form.error !== null ? ' profile-input-error' : ''}${
            form.saving ? ' profile-input-locked' : ''
          }`}
          data-testid="profile-name-input"
          value={form.value}
          placeholder="Например, Анна Ковалёва"
          readOnly={form.saving}
          onChange={(event) => form.change(event.target.value)}
        />
        {form.error !== null ? (
          <p className="profile-field-error" role="alert" data-testid="profile-name-error">
            {form.error}
          </p>
        ) : form.saving ? (
          <p className="profile-field-note">Сохраняем имя…</p>
        ) : (
          <p className="profile-field-note">
            {profile.name === null
              ? 'Пока имени нет, везде показывается адрес почты.'
              : 'Очистите поле и сохраните, чтобы убрать имя — снова будет показываться почта.'}
          </p>
        )}
      </div>

      <div className="profile-actions">
        <button
          type="button"
          className="profile-btn-ghost"
          data-testid="profile-name-cancel"
          disabled={!form.changed || form.saving}
          onClick={form.cancel}
        >
          Отмена
        </button>
        {/* Disabled while the value equals the saved one: there is nothing to send, and a live
            button invites a request that would change nothing. */}
        <button
          type="submit"
          className="profile-btn-primary"
          data-testid="profile-name-save"
          disabled={!form.canSave}
        >
          {form.saving && <span className="profile-spinner" aria-hidden="true" />}
          {form.saving ? 'Сохранение…' : 'Сохранить'}
        </button>
      </div>
    </form>
  )
}
