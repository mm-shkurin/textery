import { useRef } from 'react'
import type { Profile } from '../../../shared/identity/api/profileApi'
import { ALLOWED_AVATAR_TYPES } from '../avatarImage'
import { AVATAR_FAILED_MESSAGE } from '../profileCopy'
import { useAvatarUpload } from '../useAvatarUpload'
import './ProfileAvatarField.css'

interface ProfileAvatarFieldProps {
  profile: Profile
}

// The picture, and the two things that can be done to it.
//
// No drag-and-drop and no crop editor: a hidden <input type="file"> behind a button is the whole
// interaction, and the crop is decided for the user (centre square, 256px) rather than asked of
// them. Both were weighed and dropped — they are a day of work for an avatar.
//
// It draws NO preview disc of its own. The identity row directly above it is already showing the
// current picture at 72px and updates from the same snapshot the moment an upload lands; a second
// disc twelve pixels away would be the same image twice, and the two would look out of sync
// during the request whichever one updated first.
export function ProfileAvatarField({ profile }: ProfileAvatarFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const avatar = useAvatarUpload()
  const hasPicture = profile.avatarUpdatedAt !== null

  return (
    <div className="profile-avatar-field">
      <div className="profile-avatar-controls">
        <p className="profile-avatar-hint">
          PNG, JPEG или WebP до 10 МБ. Изображение будет уменьшено до квадрата 256×256.
        </p>

        <div className="profile-avatar-buttons">
          <button
            type="button"
            className="profile-btn-ghost"
            data-testid="avatar-upload-button"
            disabled={avatar.busy}
            // The real control is the input; this button is the only visible one because a bare
            // file input cannot be styled and reads as a form nobody designed.
            onClick={() => inputRef.current?.click()}
          >
            {avatar.busy ? 'Отправляем…' : hasPicture ? 'Заменить' : 'Загрузить'}
          </button>

          {hasPicture && (
            <button
              type="button"
              className="profile-btn-ghost"
              data-testid="avatar-delete-button"
              disabled={avatar.busy}
              onClick={() => void avatar.remove()}
            >
              Удалить
            </button>
          )}
        </div>

        {/* SVG is absent from `accept` AND from the check behind it: the attribute is a hint the
            file dialog may ignore, and a picture shown on every authenticated page is the last
            place to accept a format that can carry script. */}
        <input
          ref={inputRef}
          type="file"
          className="profile-avatar-input"
          data-testid="avatar-file-input"
          accept={ALLOWED_AVATAR_TYPES.join(',')}
          onChange={(event) => {
            const file = event.target.files?.[0]
            // Reset first: picking the SAME file twice fires no `change` at all otherwise, so a
            // user who fixed nothing and re-picked would think the app had frozen.
            event.target.value = ''
            if (file !== undefined) void avatar.upload(file)
          }}
        />

        {avatar.rejection !== null && (
          <p className="profile-avatar-rejection" role="alert" data-testid="avatar-rejection">
            {avatar.rejection}
          </p>
        )}

        {avatar.failed && (
          <div className="profile-avatar-failed" role="alert" data-testid="avatar-failed">
            <span>{AVATAR_FAILED_MESSAGE}</span>
            <button type="button" className="profile-btn-ghost" onClick={() => void avatar.retry()}>
              Повторить
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
