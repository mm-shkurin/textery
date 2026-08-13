import { ProfileAvatar } from '../../../shared/components/profile/ProfileAvatar'
import { formatCardDate } from '../../../shared/formatCardDate'
import type { Profile } from '../../../shared/identity/api/profileApi'

interface ProfileIdentityCardProps {
  profile: Profile
}

// The card's top half: who this account is (mockups 02 and 03).
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
    <div className="profile-identity">
      <ProfileAvatar identity={{ status: 'ready', profile }} size="card" />
      <div className="profile-who">
        <div className="profile-primary" data-testid="profile-identity-primary">
          {hasName ? profile.name : profile.email}
        </div>
        <div className="profile-secondary" data-testid="profile-identity-secondary">
          {hasName ? profile.email : 'Имя не задано'}
        </div>
        {/* The year is FORCED on. `formatCardDate` hides it when it matches the current year,
            which is right for «изменено 15 июля» on a project card and wrong here: «На Textery с
            3 февраля» is a sentence missing its point. */}
        <div className="profile-since" data-testid="profile-since">
          На Textery с {formatCardDate(profile.createdAt, { alwaysShowYear: true })}
        </div>
      </div>
    </div>
  )
}
