import { useNavigate } from 'react-router-dom'
import { logout } from '../../auth/utils/authSession'
import { UNSAVED_LEAVE_MESSAGE_PROFILE, useUnsavedGuard } from '../../auth/utils/useUnsavedGuard'
import { reloadIdentity } from '../../../shared/identity/identityStore'
import { useIdentity } from '../../../shared/identity/useIdentity'
import { ProfileHeader } from './ProfileHeader'
import { ProfileFooter } from './ProfileFooter'
import { ProfileAvatarField } from './ProfileAvatarField'
import { ProfileDangerZone } from './ProfileDangerZone'
import { ProfileIdentityCard } from './ProfileIdentityCard'
import { ProfileLoadFailed } from './ProfileLoadFailed'
import { ProfileNameForm } from './ProfileNameForm'
import { ProfileSkeleton } from './ProfileSkeleton'
import './ProfilePage.css'
import './ProfileForm.css'
import './ProfileStates.css'

// «Мой профиль» — mockups 01–08.
//
// A ONE-COLUMN page: the shell is 1240px, narrower than «Мои проекты» at 1640. That screen is a
// feed and wants the width; this one is a single form, and a form stretched to feed width has its
// label at one end of the monitor and its counter at the other.
//
// It reads the SAME identity snapshot the header does — one `GET /me` for the page, not one per
// component. The card and the menu therefore cannot disagree, and the failure state is shared:
// mockup 08's whole point is that a degraded header and a failed screen are one event, not two.
export function ProfilePage() {
  const identity = useIdentity()
  const navigate = useNavigate()
  // The guard lives here rather than in the form because the seam it protects is above the form:
  // signing out from the menu leaves the page too. `beforeunload` (refresh, tab close) is covered
  // by the hook itself.
  const guard = useUnsavedGuard(UNSAVED_LEAVE_MESSAGE_PROFILE)

  const handleLogout = () => {
    if (!guard.confirmLeave()) return
    logout()
    navigate('/')
  }

  return (
    <div className="profile-screen" data-testid="profile-screen">
      <ProfileHeader onLogoutClick={handleLogout} />

      <main className="profile-page">
        <h1 className="profile-heading">Мой профиль</h1>
        <p className="profile-subtitle">Данные вашей учётной записи</p>

        <div className="profile-wrap">
          <div className="profile-card">
            {identity.status === 'ready' ? (
              <>
                <ProfileIdentityCard profile={identity.profile} />
                <ProfileAvatarField profile={identity.profile} />
                <div className="profile-divider" />
                <ProfileNameForm
                  profile={identity.profile}
                  markDirty={guard.markDirty}
                  markClean={guard.markClean}
                />
              </>
            ) : identity.status === 'failed' ? (
              // A message and «Повторить», never an endless spinner: a spinner with no bound is
              // indistinguishable from a hung tab, and this request can genuinely never answer.
              <ProfileLoadFailed onRetry={reloadIdentity} onBack={() => navigate(-1)} />
            ) : (
              <ProfileSkeleton />
            )}
          </div>

          {/* Outside the card, below everything reversible. It renders only once the identity is
              known: the address IS the confirmation for an OAuth account, and the account type
              decides which field the panel shows — neither is guessable from a failed load. */}
          {identity.status === 'ready' && <ProfileDangerZone profile={identity.profile} />}
        </div>
      </main>

      <ProfileFooter />
    </div>
  )
}
