import { identityLabel } from '../../identity/identityLabel'
import type { IdentityState } from '../../identity/identityStore'
import { ProfileAvatar } from './ProfileAvatar'

interface ProfileMenuIdentityRowProps {
  identity: IdentityState
  testIdPrefix: string
}

// The panel's header row: the answer to "whose account am I in", and nothing else.
//
// NOT a menu item. It gets no `role="menuitem"` and is never focusable — giving it one would
// announce an identity label as something to activate. That is why it is a <div> next to two
// <button>s, which reads like an oversight and is not.
//
// It says something DEFINITE in all three states. A failed request that silently rendered nothing
// would read as "an account with no name" — the one reading the whole degraded treatment exists
// to prevent. The previous identity is deliberately NOT shown after a failure: a session may have
// changed underneath, and a stale identity there is somebody else's account leaking, not a
// slightly old name.
export function ProfileMenuIdentityRow({ identity, testIdPrefix }: ProfileMenuIdentityRowProps) {
  return (
    <div className="profile-panel-account">
      <ProfileAvatar identity={identity} size="menu" />
      {identity.status === 'ready' ? (
        <span className="profile-panel-email" data-testid={`${testIdPrefix}-profile-email`}>
          {identityLabel(identity.profile)}
        </span>
      ) : identity.status === 'failed' ? (
        <span className="profile-panel-degraded" data-testid={`${testIdPrefix}-profile-degraded`}>
          Данные профиля недоступны
        </span>
      ) : (
        <span className="profile-panel-skeleton profile-shimmer" aria-hidden="true" />
      )}
    </div>
  )
}
