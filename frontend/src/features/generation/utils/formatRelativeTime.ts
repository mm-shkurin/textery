export function formatRelativeTime(isoDate: string | null): string {
  if (!isoDate) return 'создан только что'

  const created = new Date(isoDate).getTime()
  if (Number.isNaN(created)) return 'создан только что'

  const diffSeconds = Math.max(0, Math.floor((Date.now() - created) / 1000))
  if (diffSeconds < 60) return 'создан только что'

  const diffMinutes = Math.floor(diffSeconds / 60)
  if (diffMinutes < 60) return `создан ${diffMinutes} мин назад`

  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `создан ${diffHours} ч назад`

  const diffDays = Math.floor(diffHours / 24)
  return `создан ${diffDays} дн назад`
}
