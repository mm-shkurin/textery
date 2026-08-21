import profilePageStyles from './ProfilePage.module.css'
import profileStatesStyles from './ProfileStates.module.css'
import profileMenuStyles from '../../../shared/components/profile/ProfileMenu.module.css'

// Mockup 01. A DEFINED placeholder in the shape of the card that is coming — a disc where the
// disc goes, lines where the lines go — never a blank avatar that pops into initials a moment
// later. Since the header moved onto `/me`, this state is every page for the length of a request
// rather than an edge case, so its cost is paid on every navigation.
//
// `aria-hidden`, because it says nothing: a screen reader announcing three empty boxes is worse
// than silence while the real content is on its way.
export function ProfileSkeleton() {
  return (
    <div className="profile-skeleton" data-testid="profile-loading" aria-hidden="true">
      <div className={profilePageStyles['profile-identity']}>
        <span
          className={`${profileStatesStyles['profile-skeleton-avatar']} ${profileMenuStyles['profile-shimmer']}`}
        />
        <div className={profilePageStyles['profile-who']}>
          <span
            className={`${profileMenuStyles['profile-shimmer']} ${profileStatesStyles['profile-skeleton-line']} ${profileStatesStyles['profile-skeleton-line-lg']}`}
          />
          <span
            className={`${profileMenuStyles['profile-shimmer']} ${profileStatesStyles['profile-skeleton-line']} ${profileStatesStyles['profile-skeleton-line-md']}`}
          />
          <span
            className={`${profileMenuStyles['profile-shimmer']} ${profileStatesStyles['profile-skeleton-line']} ${profileStatesStyles['profile-skeleton-line-sm']}`}
          />
        </div>
      </div>
      <div className={profileStatesStyles['profile-divider']} />
      <span
        className={`${profileMenuStyles['profile-shimmer']} ${profileStatesStyles['profile-skeleton-input']}`}
      />
    </div>
  )
}
