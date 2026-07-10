import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { formatRelativeTime } from '../formatRelativeTime'

const NOW = new Date('2026-01-10T12:00:00Z').getTime()

function isoSecondsAgo(seconds: number): string {
  return new Date(NOW - seconds * 1000).toISOString()
}

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns "just now" for null date', () => {
    expect(formatRelativeTime(null)).toBe('создан только что')
  })

  it('returns "just now" for invalid date', () => {
    expect(formatRelativeTime('not-a-date')).toBe('создан только что')
  })

  it('returns "just now" under the 60 second boundary', () => {
    expect(formatRelativeTime(isoSecondsAgo(59))).toBe('создан только что')
  })

  it('returns minutes at the 60 second boundary', () => {
    expect(formatRelativeTime(isoSecondsAgo(60))).toBe('создан 1 мин назад')
  })

  it('returns minutes under the 60 minute boundary', () => {
    expect(formatRelativeTime(isoSecondsAgo(59 * 60))).toBe('создан 59 мин назад')
  })

  it('returns hours at the 60 minute boundary', () => {
    expect(formatRelativeTime(isoSecondsAgo(60 * 60))).toBe('создан 1 ч назад')
  })

  it('returns hours under the 24 hour boundary', () => {
    expect(formatRelativeTime(isoSecondsAgo(23 * 60 * 60))).toBe('создан 23 ч назад')
  })

  it('returns days at the 24 hour boundary', () => {
    expect(formatRelativeTime(isoSecondsAgo(24 * 60 * 60))).toBe('создан 1 дн назад')
  })
})
