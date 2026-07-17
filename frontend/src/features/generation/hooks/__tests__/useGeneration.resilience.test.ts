import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useGeneration } from '../useGeneration'
import { SessionExpiredError } from '../../../auth/api/authorizedRequest'
import * as api from '../../api/generationApi'

vi.mock('../../api/generationApi')

const PENDING = {
  generationId: 'gen-1',
  status: 'pending',
  content: null,
  topic: 't',
  volumePages: 5,
  documentType: 'doklad',
  createdAt: 'now',
}
const COMPLETED = { ...PENDING, status: 'completed', content: '<p>готово</p>' }

// The generation runs on the SERVER for minutes. A missed status check is not a failed
// generation — only giving up on it is. This poll used to stop and report `failed` on the very
// first rejection, so one 502 from the proxy during a ~5-minute wait threw away a document that
// was still being written and told the user it had failed.
describe('useGeneration — a status check that misses is not a generation that failed', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  async function startPolling() {
    vi.mocked(api.createGeneration).mockResolvedValue({ generationId: 'gen-1', status: 'pending' })
    const hook = renderHook(() => useGeneration())
    await act(async () => {
      hook.result.current.submit('тема')
    })
    return hook
  }

  async function tick() {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000)
    })
  }

  it('rides out a transient failure and completes the generation', async () => {
    vi.mocked(api.getGeneration)
      .mockRejectedValueOnce(new Error('Не удалось получить статус (HTTP 502)'))
      .mockResolvedValueOnce(COMPLETED)

    const { result } = await startPolling()

    // Still waiting, not failed — the 502 was the proxy's, not the generation's.
    expect(result.current.state).toBe('pending')

    await tick()

    expect(result.current.state).toBe('completed')
    expect(result.current.content).toBe('<p>готово</p>')
  })

  it('gives up once the checks fail three times in a row', async () => {
    vi.mocked(api.getGeneration).mockRejectedValue(new Error('Ошибка сети'))

    const { result } = await startPolling()
    await tick()
    expect(result.current.state).toBe('pending')

    await tick()

    // A status endpoint that is genuinely down must be reported promptly, not retried in silence.
    expect(result.current.state).toBe('failed')
    expect(result.current.error).toBe('Ошибка сети')
  })

  // The counter is CONSECUTIVE. A poll that misses once every few minutes must ride out the whole
  // generation rather than accumulate toward the limit across unrelated blips.
  it('forgets earlier failures once a check succeeds', async () => {
    vi.mocked(api.getGeneration)
      .mockRejectedValueOnce(new Error('blip'))
      .mockRejectedValueOnce(new Error('blip'))
      .mockResolvedValueOnce(PENDING)
      .mockRejectedValueOnce(new Error('blip'))
      .mockRejectedValueOnce(new Error('blip'))
      .mockResolvedValueOnce(COMPLETED)

    const { result } = await startPolling()
    for (let i = 0; i < 5; i += 1) await tick()

    // Five failures total, never three in a row: the generation survives.
    expect(result.current.state).toBe('completed')
  })

  // An expired session will not fix itself by asking again — every further attempt is a
  // guaranteed 401, so tolerance here would only delay the truth by fifteen seconds.
  it('stops immediately when the session has expired, and says so', async () => {
    vi.mocked(api.getGeneration).mockRejectedValue(new SessionExpiredError())

    const { result } = await startPolling()

    expect(result.current.state).toBe('failed')
    expect(result.current.error).toBe('Сессия истекла. Войдите снова.')
  })
})
