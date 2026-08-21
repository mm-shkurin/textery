import { setThemePreference } from '../../../shared/theme/themeStore'
import { useThemePreference } from '../../../shared/theme/useThemePreference'
import type { ThemePreference } from '../../../shared/theme/theme'
import profileThemeStyles from './ProfileTheme.module.css'

const SEGMENTS: { value: ThemePreference; label: string }[] = [
  { value: 'system', label: 'Системная' },
  { value: 'light', label: 'Светлая' },
  { value: 'dark', label: 'Темная' },
]

// The «Внешний вид» segmented control — Figma node 1127:10768, the 289×48 track at x=1446.
//
// A RADIO GROUP, not three buttons: these are three mutually exclusive states of one setting, and
// the arrow-key behaviour a user gets for free from real radios is the behaviour a fake one has to
// re-implement by hand and usually doesn't. The inputs are the control; the pills are their labels.
//
// It does NOT replace the toggle in the account menu — that one has its own Selenium test, it
// belongs to another session's file, and two ways to reach one setting is what the design draws.
export function ProfileThemeSwitch() {
  const preference = useThemePreference()

  return (
    <div
      className={profileThemeStyles['profile-theme-switch']}
      role="radiogroup"
      aria-label="Тема оформления"
    >
      {SEGMENTS.map((segment) => (
        <label
          key={segment.value}
          className={`${profileThemeStyles['profile-theme-segment']}${
            preference === segment.value ? ' ' + profileThemeStyles['profile-theme-segment-on'] : ''
          }`}
        >
          <input
            type="radio"
            name="profile-theme"
            className={profileThemeStyles['profile-theme-radio']}
            value={segment.value}
            checked={preference === segment.value}
            data-testid={`profile-theme-${segment.value}`}
            onChange={() => setThemePreference(segment.value)}
          />
          {segment.label}
        </label>
      ))}
    </div>
  )
}
