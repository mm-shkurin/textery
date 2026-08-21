import { EARLIEST_PLAUSIBLE_YEAR, LATEST_PLAUSIBLE_YEAR } from './config/runtime'

// Day + month for this year, day + month + year for anything older — both formats are in the
// mockup (`15 июля` alongside `2 сентября 2025` and `16 декабря 2024`). Dropping the year
// unconditionally would render a 2024 project as `16 декабря`, indistinguishable from one
// finished this month, on the screen whose whole job is telling the user's work apart.
//
// The wire sends UTC ISO; toLocaleDateString renders it in the reader's zone, and the year is
// compared in that same zone so a 31 December evening does not read as next year's.
//
// The year is appended by hand rather than asked of the formatter: ru-RU's `year: 'numeric'`
// emits the era suffix ('2 сентября 2025 г.') and the mockup does not. The formatter still owns
// the day and the genitive month, which is the part worth not hand-rolling.
//
// `updatedAt: string` is a compile-time claim about a runtime JSON body from an endpoint the
// backend has not built, so both guards below are about values the type system says cannot arrive.
// The INPUT is guarded, not the resulting epoch value: `new Date(null)` is a perfectly valid Date
// reading 1 января 1970, which no `isNaN` check catches and which the user reads as a real edit
// date. A `getTime() === 0` guard would satisfy the same two tests while blanking a genuine
// 1970-01-01 — a different bug. `—` rather than an empty slot, matching `HistoryPage`'s
// `formatDate`, which has shipped that placeholder for the same condition since before this screen.
const UNUSABLE_DATE = '—'

// A backend sentinel arrives as a perfectly shaped, perfectly parseable ISO string. Neither shape
// guard above can see it; only its VALUE is wrong. So the year is bounded — by the shared tunables
// in `shared/config/runtime`, which carry the reasoning for the two numbers.

// Lives outside `ProjectCard.tsx` because it is pure formatting over a wire string with a guard
// stack of its own — the same shape as `generation/formatRelativeTime.ts` and
// `auth/utils/formatDuration.ts`, and the thing the card's date tests are actually about. It is
// NOT shared with `HistoryPage`'s `formatDate`: that one always renders the year (era suffix and
// all) and knows nothing about sentinel bounds. The overlap is two lines of em-dash fallback;
// unifying them would mean a mode flag threaded through both screens' contracts.
interface FormatCardDateOptions {
  // Hiding the year when it matches the current one is right for «последнее изменение» on a
  // project card — «15 июля» reads as recent because it is. It is wrong for «На Textery с …»,
  // where the year is half the fact and an account opened this January would render as
  // «3 февраля», indistinguishable from a date with no year at all. The flag is opt-in so the
  // feed keeps the behaviour its own tests pin.
  alwaysShowYear?: boolean
}

export function formatCardDate(iso: string, options: FormatCardDateOptions = {}): string {
  if (typeof iso !== 'string') return UNUSABLE_DATE
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return UNUSABLE_DATE
  const parsedYear = date.getFullYear()
  if (parsedYear < EARLIEST_PLAUSIBLE_YEAR || parsedYear > LATEST_PLAUSIBLE_YEAR) {
    return UNUSABLE_DATE
  }
  const dayAndMonth = date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' })
  const showYear = options.alwaysShowYear === true || parsedYear !== new Date().getFullYear()
  return showYear ? `${dayAndMonth} ${parsedYear}` : dayAndMonth
}
