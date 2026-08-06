import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, renderHook } from '@testing-library/react'
import { useProjectView, VIEW_STORAGE_KEY } from '../useProjectView'

// A device-local preference read from `localStorage`, which means three of this hook's four paths
// are about storage misbehaving rather than about the toggle. Private-mode Safari and some
// enterprise policies make both `getItem` and `setItem` THROW, and an unguarded read there takes
// the whole feed down for a preference nobody would miss — so the catch arms are the point of
// this suite, not an afterthought.
describe('useProjectView', () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
  })

  it('starts on the grid when nothing was ever chosen', () => {
    const { result } = renderHook(() => useProjectView())
    expect(result.current[0]).toBe('grid')
  })

  it('restores the stored choice', () => {
    window.localStorage.setItem(VIEW_STORAGE_KEY, 'list')
    const { result } = renderHook(() => useProjectView())
    expect(result.current[0]).toBe('list')
  })

  // An older build, a hand-edited entry, or a key another feature reused: anything this build does
  // not recognise falls back rather than leaving the feed with no view at all.
  it.each([['table'], [''], ['LIST']])(
    'falls back to the grid on the stored value %s',
    (stored) => {
      window.localStorage.setItem(VIEW_STORAGE_KEY, stored)
      const { result } = renderHook(() => useProjectView())
      expect(result.current[0]).toBe('grid')
    },
  )

  it('remembers a choice for the next visit', () => {
    const { result } = renderHook(() => useProjectView())

    act(() => result.current[1]('list'))

    expect(result.current[0]).toBe('list')
    expect(window.localStorage.getItem(VIEW_STORAGE_KEY)).toBe('list')
  })

  it('remembers a choice back to the grid', () => {
    window.localStorage.setItem(VIEW_STORAGE_KEY, 'list')
    const { result } = renderHook(() => useProjectView())

    act(() => result.current[1]('grid'))

    expect(result.current[0]).toBe('grid')
    expect(window.localStorage.getItem(VIEW_STORAGE_KEY)).toBe('grid')
  })

  it('renders the default view when reading storage throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('SecurityError')
    })

    const { result } = renderHook(() => useProjectView())

    expect(result.current[0]).toBe('grid')
  })

  // The toggle keeps working for this session even when the choice cannot be persisted. Asserted
  // as state changing, not merely as "no throw": a catch that also swallowed the `setView` would
  // leave the user clicking a control that does nothing.
  it('keeps the toggle working for this session when writing storage throws', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('QuotaExceededError')
    })
    const { result } = renderHook(() => useProjectView())

    act(() => result.current[1]('list'))

    expect(result.current[0]).toBe('list')
  })
})
