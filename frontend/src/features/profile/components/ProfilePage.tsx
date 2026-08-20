import { useNavigate } from 'react-router-dom'
import { logout } from '../../../shared/session/authSession'
import {
  UNSAVED_LEAVE_MESSAGE_PROFILE,
  useUnsavedGuard,
} from '../../../shared/hooks/useUnsavedGuard'
import { reloadIdentity } from '../../../shared/identity/identityStore'
import { useIdentity } from '../../../shared/identity/useIdentity'
import { ProfileHeader } from './ProfileHeader'
import { ProfileAccountCard } from './ProfileAccountCard'
import { ProfileAppearanceCard } from './ProfileAppearanceCard'
import { ProfileLoadFailed } from './ProfileLoadFailed'
import { ProfilePersonalCard } from './ProfilePersonalCard'
import { ProfileSkeleton } from './ProfileSkeleton'
import styles from './ProfilePage.module.css'
import './ProfileButtons.module.css'
import './ProfileForm.module.css'
import './ProfileTheme.module.css'
import './ProfileModal.module.css'
import './ProfileStates.module.css'

// «Мой профиль» — Figma nodes 1127:10768 (base), 1202:6364 (editing), 1227:9790 (saving) and
// 1202:6227 (deleting).
//
// THREE cards, not one: personal data, appearance, account. The split is the design's and it is
// the right one — «выйти» and «удалить аккаунт» are not personal data, and burying them under the
// same heading as a display name is how a user ends up hunting for the way out.
//
// Every card reads the SAME identity snapshot the header does — one `GET /me` for the page, not
// one per component. The cards and the menu therefore cannot disagree, and the failure state is
// shared: a degraded header and a failed screen are one event, not two.
export function ProfilePage() {
  const identity = useIdentity()
  const navigate = useNavigate()
  // The guard lives here rather than in the form because the seam it protects is above the form:
  // signing out from the menu — or from the account card — leaves the page too. `beforeunload`
  // (refresh, tab close) is covered by the hook itself.
  const guard = useUnsavedGuard(UNSAVED_LEAVE_MESSAGE_PROFILE)

  const handleLogout = () => {
    if (!guard.confirmLeave()) return
    logout()
    navigate('/')
  }

  // The bar's «Мои проекты». An explicit destination, not `navigate(-1)`: this screen is reachable
  // straight from the URL and from a fresh tab, where there is no history entry to go back to and
  // the browser would leave the product entirely.
  const handleBack = () => {
    if (!guard.confirmLeave()) return
    navigate('/projects')
  }

  return (
    <div className={styles['profile-screen']} data-testid="profile-screen">
      <ProfileHeader onLogoutClick={handleLogout} onProjectsClick={handleBack} />

      <main className={styles['profile-page']}>
        <h1 className={styles['profile-heading']}>Мой профиль</h1>
        <p className={styles['profile-subtitle']}>
          Личные данные, внешний вид приложения и управление аккаунтом
        </p>

        {identity.status === 'ready' ? (
          <>
            <ProfilePersonalCard
              profile={identity.profile}
              markDirty={guard.markDirty}
              markClean={guard.markClean}
            />
            <ProfileAppearanceCard />
            {/* Renders only once the identity is known: the address IS the confirmation for an
                OAuth account, and the account type decides which field the dialog shows — neither
                is guessable from a failed load. */}
            <ProfileAccountCard profile={identity.profile} onLogoutClick={handleLogout} />
          </>
        ) : identity.status === 'failed' ? (
          // A message and «Повторить», never an endless spinner: a spinner with no bound is
          // indistinguishable from a hung tab, and this request can genuinely never answer.
          <div className={styles['profile-card']}>
            <ProfileLoadFailed onRetry={reloadIdentity} onBack={() => navigate(-1)} />
          </div>
        ) : (
          <div className={styles['profile-card']}>
            <ProfileSkeleton />
          </div>
        )}
      </main>
    </div>
  )
}
