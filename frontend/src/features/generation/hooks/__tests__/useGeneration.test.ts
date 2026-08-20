import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useGeneration } from '../useGeneration'
import * as api from '../../api/generationApi'
import { fromWire } from '../../../../test/doubles'

vi.mock('../../api/generationApi')

describe('useGeneration', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('transitions idle -> pending -> completed after polling', async () => {
    vi.mocked(api.createGeneration).mockResolvedValue({ generationId: 'gen-1', status: 'pending' })
    vi.mocked(api.getGeneration)
      .mockResolvedValueOnce({
        generationId: 'gen-1',
        status: 'pending',
        content: null,
        topic: 't',
        volumePages: 5,
        documentType: 'doklad',
        createdAt: 'now',
      })
      .mockResolvedValueOnce({
        generationId: 'gen-1',
        status: 'completed',
        content: '# Готово',
        topic: 't',
        volumePages: 5,
        documentType: 'doklad',
        createdAt: 'now',
      })

    const { result } = renderHook(() => useGeneration())

    await act(async () => {
      result.current.submit('тема')
    })
    expect(result.current.state).toBe('pending')

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })

    expect(result.current.state).toBe('completed')
    expect(result.current.content).toBe('# Готово')
    expect(result.current.volumePages).toBe(5)
  })

  it('stops polling and fails after max attempts exceeded', async () => {
    vi.mocked(api.createGeneration).mockResolvedValue({ generationId: 'gen-1', status: 'pending' })
    vi.mocked(api.getGeneration).mockResolvedValue({
      generationId: 'gen-1',
      status: 'pending',
      content: null,
      topic: 't',
      volumePages: 5,
      documentType: 'doklad',
      createdAt: 'now',
    })

    const { result } = renderHook(() => useGeneration())

    await act(async () => {
      result.current.submit('тема')
    })

    // The gap between checks grows to a 30s ceiling, so the attempt budget takes longer in wall
    // time than 61 x 5s. Advancing past the worst case spends it either way.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30000 * 62)
    })

    expect(result.current.state).toBe('failed')
    expect(result.current.error).toMatch(/время ожидания/)
  })

  it('reset clears state and stops polling', async () => {
    vi.mocked(api.createGeneration).mockResolvedValue({ generationId: 'gen-1', status: 'pending' })
    vi.mocked(api.getGeneration).mockResolvedValue({
      generationId: 'gen-1',
      status: 'pending',
      content: null,
      topic: 't',
      // The wire may omit a page count entirely; the type says it cannot.
      volumePages: fromWire<number>('null'),
      documentType: 'doklad',
      createdAt: 'now',
    })

    const { result } = renderHook(() => useGeneration())

    await act(async () => {
      result.current.submit('тема')
    })

    act(() => {
      result.current.reset()
    })

    expect(result.current.state).toBe('idle')
    expect(result.current.content).toBeNull()
  })
})
