import type { Profile } from '../../../shared/identity/api/profileApi'
import { DELETION_TITLE, DELETION_WARNING } from '../utils/profileCopy'
import { useAccountDeletion } from '../hooks/useAccountDeletion'
import { ProfileDeleteModal } from './ProfileDeleteModal'
import profilePageStyles from './ProfilePage.module.css'
import profileButtonsStyles from './ProfileButtons.module.css'

interface ProfileAccountCardProps {
  profile: Profile
  onLogoutClick: () => void
}

// The last of the three cards — Figma node 1127:10768, the 1640×307 panel at y=1045.
//
// Two rows that both end the session, ordered by how far they go: signing out is reversible by
// signing back in, and the row under it is the only irreversible thing in the product. They share
// a card in the design and they should: a user looking for the way out finds both, and the second
// one is visibly the heavier of the two rather than hidden somewhere they would only find it by
// accident.
export function ProfileAccountCard({ profile, onLogoutClick }: ProfileAccountCardProps) {
  const deletion = useAccountDeletion(profile)

  return (
    <section className={profilePageStyles['profile-card']} data-testid="profile-danger-zone">
      <h2 className={profilePageStyles['profile-card-title']}>Аккаунт</h2>
      <p className={profilePageStyles['profile-card-subtitle']}>
        Выход из системы и управление данными
      </p>

      <div
        className={`${profileButtonsStyles['profile-row']} ${profilePageStyles['profile-row']} ${profilePageStyles['profile-row-divided']}`}
      >
        <div>
          <div className={profilePageStyles['profile-row-label']}>Выйти из аккаунта</div>
          <div className={profilePageStyles['profile-row-value']}>
            Завершить сеанс на этом устройстве
          </div>
        </div>
        <button
          type="button"
          className={profileButtonsStyles['profile-btn-ghost']}
          data-testid="profile-logout-button"
          onClick={onLogoutClick}
        >
          Выйти
        </button>
      </div>

      <div
        className={`${profileButtonsStyles['profile-row']} ${profilePageStyles['profile-row']} ${profilePageStyles['profile-row-divided']}`}
      >
        <div>
          <div className={profilePageStyles['profile-row-label']}>{DELETION_TITLE}</div>
          {/* The one sentence that says what "delete my account" actually costs. It names the
              documents and the generations, not just "your account": those are the user's own
              texts, and this is the only place in the product where anyone finds out they go too.
              It is not here to frighten anybody out of leaving — it is here so that nobody leaves
              without knowing. */}
          <div className={profilePageStyles['profile-row-value']}>{DELETION_WARNING}</div>
        </div>
        <button
          type="button"
          className={profileButtonsStyles['profile-btn-danger']}
          data-testid="account-delete-button"
          onClick={deletion.openConfirmation}
        >
          Удалить аккаунт
        </button>
      </div>

      {/* The button opens a confirmation and never deletes anything itself. The dialog asks for one
          specific thing the user knows — their password, or their own address — rather than a
          second «вы уверены?», which people click through without reading. */}
      {deletion.open && <ProfileDeleteModal profile={profile} deletion={deletion} />}
    </section>
  )
}
