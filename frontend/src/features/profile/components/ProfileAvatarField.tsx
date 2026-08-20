import { useRef } from 'react'
import type { Profile } from '../../../shared/identity/api/profileApi'
import { ALLOWED_AVATAR_TYPES } from '../utils/avatarImage'
import { AVATAR_FAILED_MESSAGE } from '../utils/profileCopy'
import { useAvatarUpload } from '../hooks/useAvatarUpload'
import { ProfileSavedToast } from './ProfileSavedToast'
import profileFormStyles from './ProfileForm.module.css'
import profileButtonsStyles from './ProfileButtons.module.css'

interface ProfileAvatarFieldProps {
  profile: Profile
}

// The two controls the design puts at the right end of the picture row — Figma node 1127:10768,
// the 175px text button at x=1406 and the 144px outlined one at x=1592.
//
// No drag-and-drop and no crop editor: a hidden <input type="file"> behind a button is the whole
// interaction, and the crop is decided for the user (centre square, 256px) rather than asked of
// them. Both were weighed and dropped — they are a day of work for an avatar.
//
// It draws NO preview disc of its own. The row it sits in already shows the current picture and
// updates from the same snapshot the moment an upload lands; a second disc a few pixels away would
// be the same image twice, and the two would look out of sync during the request whichever one
// updated first.
export function ProfileAvatarField({ profile }: ProfileAvatarFieldProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const avatar = useAvatarUpload()
  const hasPicture = profile.avatarUpdatedAt !== null

  return (
    <div className={profileFormStyles['profile-avatar-field']}>
      {/* Same confirmation as the name form's, for the same reason: an upload that finishes by
          re-rendering one 64px disc is a change a user can easily miss. */}
      <ProfileSavedToast saveCount={avatar.savedCount} />
      <div className={profileFormStyles['profile-avatar-buttons']}>
        {/* «Удалить фото» first, matching the mockup's order — and it exists only when there is a
            picture to delete, so the row does not offer to remove nothing. */}
        {hasPicture && (
          <button
            type="button"
            className={profileButtonsStyles['profile-btn-quiet']}
            data-testid="avatar-delete-button"
            disabled={avatar.busy}
            onClick={() => void avatar.remove()}
          >
            Удалить фото
          </button>
        )}

        <button
          type="button"
          className={profileButtonsStyles['profile-btn-ghost']}
          data-testid="avatar-upload-button"
          disabled={avatar.busy}
          // The real control is the input; this button is the only visible one because a bare file
          // input cannot be styled and reads as a form nobody designed.
          onClick={() => inputRef.current?.click()}
        >
          {avatar.busy ? 'Отправляем…' : 'Изменить'}
        </button>
      </div>

      {/* SVG is absent from `accept` AND from the check behind it: the attribute is a hint the file
          dialog may ignore, and a picture shown on every authenticated page is the last place to
          accept a format that can carry script. */}
      <input
        ref={inputRef}
        type="file"
        className={profileFormStyles['profile-avatar-input']}
        data-testid="avatar-file-input"
        accept={ALLOWED_AVATAR_TYPES.join(',')}
        onChange={(event) => {
          const file = event.target.files?.[0]
          // Reset first: picking the SAME file twice fires no `change` at all otherwise, so a user
          // who fixed nothing and re-picked would think the app had frozen.
          event.target.value = ''
          if (file !== undefined) void avatar.upload(file)
        }}
      />

      {avatar.rejection !== null && (
        <p
          className={profileFormStyles['profile-avatar-rejection']}
          role="alert"
          data-testid="avatar-rejection"
        >
          {avatar.rejection}
        </p>
      )}

      {avatar.failed && (
        <div
          className={profileFormStyles['profile-avatar-failed']}
          role="alert"
          data-testid="avatar-failed"
        >
          <span>{AVATAR_FAILED_MESSAGE}</span>
          <button
            type="button"
            className={profileButtonsStyles['profile-btn-ghost']}
            onClick={() => void avatar.retry()}
          >
            Повторить
          </button>
        </div>
      )}
    </div>
  )
}
