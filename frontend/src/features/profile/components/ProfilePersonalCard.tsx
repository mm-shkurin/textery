import { ProfileAvatar } from '../../../shared/components/profile/ProfileAvatar'
import type { Profile } from '../../../shared/identity/api/profileApi'
import { ProfileAvatarField } from './ProfileAvatarField'
import { ProfileIdentityCard } from './ProfileIdentityCard'
import { ProfileNameForm } from './ProfileNameForm'
import profilePageStyles from './ProfilePage.module.css'
import profileButtonsStyles from './ProfileButtons.module.css'

interface ProfilePersonalCardProps {
  profile: Profile
  markDirty: () => void
  markClean: () => void
}

// The first of the three cards — Figma node 1127:10768, the 1640×491 panel at y=287.
//
// The mockup's name row is a READ line with an «Изменить» button that swaps it for the form in node
// 1202:6364. This renders that form permanently instead, and the reason is not taste: the Selenium
// suite reaches `profile-name-input` immediately after landing on the screen and checks its value
// again after a save, with no step in between that could click «Изменить». Those statements live in
// `acceptance/`, which this session does not own. A collapsed row would turn ten passing tests red
// to save one click.
export function ProfilePersonalCard({ profile, markDirty, markClean }: ProfilePersonalCardProps) {
  return (
    <section className={profilePageStyles['profile-card']}>
      <h2 className={profilePageStyles['profile-card-title']}>Личные данные</h2>

      <div
        className={`${profileButtonsStyles['profile-row']} ${profilePageStyles['profile-row']} ${profilePageStyles['profile-row-divided']}`}
      >
        <div className={profilePageStyles['profile-identity']}>
          <ProfileAvatar identity={{ status: 'ready', profile }} size="card" />
          <ProfileIdentityCard profile={profile} />
        </div>
        <ProfileAvatarField profile={profile} />
      </div>

      <ProfileNameForm profile={profile} markDirty={markDirty} markClean={markClean} />
    </section>
  )
}
