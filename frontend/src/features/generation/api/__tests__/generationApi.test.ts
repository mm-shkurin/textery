import { afterEach, describe, expect, it, vi } from 'vitest'
import { createGeneration, getGeneration } from '../generationApi'

describe('generationApi', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('createGeneration posts topic and returns generationId + status', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ generation_id: 'gen-1', status: 'pending' }),
    })
    vi.stubGlobal('fetch', fetchMock)

    const result = await createGeneration('Квантовые компьютеры')

    expect(result).toEqual({ generationId: 'gen-1', status: 'pending' })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toContain('/api/v1/generations')
    expect(JSON.parse(init.body)).toMatchObject({
      topic: 'Квантовые компьютеры',
      document_type: 'doklad',
      volume_pages: 5,
    })
  })

  it('createGeneration surfaces server error detail on non-OK response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({ detail: 'Тема слишком короткая' }),
      }),
    )

    await expect(createGeneration('x')).rejects.toThrow('Тема слишком короткая')
  })

  it('createGeneration falls back to generic message when body has no detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('not json')
        },
      }),
    )

    await expect(createGeneration('x')).rejects.toThrow('HTTP 500')
  })

  it('getGeneration maps snake_case response to GenerationStatus', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          generation_id: 'gen-1',
          status: 'completed',
          content: '# Доклад',
          topic: 'Тема',
          volume_pages: 7,
          document_type: 'doklad',
          created_at: '2026-07-10T00:00:00Z',
        }),
      }),
    )

    const result = await getGeneration('gen-1')

    expect(result.volumePages).toBe(7)
    expect(result.content).toBe('# Доклад')
  })
})
