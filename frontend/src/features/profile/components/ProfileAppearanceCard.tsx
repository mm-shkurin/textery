import { ProfileThemeSwitch } from './ProfileThemeSwitch'
import profilePageStyles from './ProfilePage.module.css'
import profileButtonsStyles from './ProfileButtons.module.css'

// The middle card of the three the design draws — Figma node 1127:10768, the 1640×221 panel at
// y=801.
//
// «на этом устройстве» is not filler: the choice is kept in `localStorage` and never sent to the
// server, so the same account on a second machine keeps that machine's theme. A subtitle that
// promised an account-wide setting would be describing a feature that does not exist.
export function ProfileAppearanceCard() {
  return (
    <section className={profilePageStyles['profile-card']} data-testid="profile-appearance">
      <h2 className={profilePageStyles['profile-card-title']}>Внешний вид</h2>
      <p className={profilePageStyles['profile-card-subtitle']}>
        Оформление интерфейса на этом устройстве
      </p>

      <div
        className={`${profileButtonsStyles['profile-row']} ${profilePageStyles['profile-row']} ${profilePageStyles['profile-row-divided']}`}
      >
        <div className={profilePageStyles['profile-row-label']}>Тема оформления</div>
        <ProfileThemeSwitch />
      </div>
    </section>
  )
}
