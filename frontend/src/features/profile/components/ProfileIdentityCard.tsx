import { formatCardDate } from '../../../shared/formatCardDate'
import type { Profile } from '../../../shared/identity/api/profileApi'
import profilePageStyles from './ProfilePage.module.css'

interface ProfileIdentityCardProps {
  profile: Profile
}

// Who this account is, in the row the design gives to the picture.
//
// The mockup labels that row «Фото профиля». This says who the account belongs to instead: the
// name, the address and the join date have to be on this screen somewhere — they are the account —
// and the mockup's three cards give them no other row. A label naming the control next to it is
// the cheapest thing on the screen to lose.
//
// With a name, the name is the headline and the address is the second line. Without one, the
// ADDRESS is the headline and the second line says so in words — «Имя не задано» rather than an
// empty row, which would read as a rendering bug on the screen whose job is showing the account.
//
// Both values are rendered as text nodes. `name` is free user input echoed into the header of
// every authenticated page, which makes it the widest stored-XSS surface in the product; React
// escapes children by default and nothing here opts out.
export function ProfileIdentityCard({ profile }: ProfileIdentityCardProps) {
  const hasName = (profile.name?.trim() ?? '') !== ''

  return (
    <div className={profilePageStyles['profile-who']}>
      <div className={profilePageStyles['profile-primary']} data-testid="profile-identity-primary">
        {hasName ? profile.name : profile.email}
      </div>
      <div
        className={profilePageStyles['profile-secondary']}
        data-testid="profile-identity-secondary"
      >
        {hasName ? profile.email : 'Имя не задано'}
      </div>
      {/* The year is FORCED on. `formatCardDate` hides it when it matches the current year, which
          is right for «изменено 15 июля» on a project card and wrong here: «На Textery с 3 февраля»
          is a sentence missing its point. */}
      <div className={profilePageStyles['profile-since']} data-testid="profile-since">
        На Textery с {formatCardDate(profile.createdAt, { alwaysShowYear: true })}
      </div>
    </div>
  )
}
