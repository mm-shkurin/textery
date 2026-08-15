import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createGeneration } from '../generationApi'
import * as send from '../../../../shared/api/send'
import { EMPTY_PARAMETERS } from '../../utils/generationParameters'

vi.mock('../../../../shared/api/send')

function postedBody() {
  const [, options] = vi.mocked(send.send).mock.calls[0]
  return (options as { body: Record<string, unknown> }).body
}

describe('the generation parameters on the wire', () => {
  beforeEach(() => {
    // Cleared, not merely re-stubbed: `postedBody` reads `mock.calls[0]`, so without this every
    // test after the first would assert against the first one's request and pass or fail for a
    // reason that has nothing to do with it.
    vi.clearAllMocks()
    vi.mocked(send.send).mockResolvedValue({ generation_id: 'g-1', status: 'pending' })
  })

  // The defect: the client sent a hardcoded `volume_pages: 5` and never sent требования or
  // пожелания at all, so two fields the domain validates, stores and echoes back were
  // unreachable from the app that collects them.
  it('sends the volume the user chose, not a constant', async () => {
    await createGeneration('Тема', 'doklad', { ...EMPTY_PARAMETERS, volumePages: 9 })

    expect(postedBody().volume_pages).toBe(9)
  })

  it('sends both text fields under their contract names', async () => {
    await createGeneration('Тема', 'doklad', {
      volumePages: 3,
      requirements: 'Официально-деловой стиль',
      extraWishes: 'Добавь пример',
    })

    expect(postedBody()).toMatchObject({
      requirements: 'Официально-деловой стиль',
      extra_wishes: 'Добавь пример',
    })
  })

  it('trims the text fields before sending them', async () => {
    await createGeneration('Тема', 'doklad', {
      ...EMPTY_PARAMETERS,
      requirements: '  Кратко  ',
    })

    expect(postedBody().requirements).toBe('Кратко')
  })

  it.each([
    ['empty', ''],
    ['whitespace only', '   '],
  ])('omits a %s field rather than sending an empty string', async (_case, value) => {
    // Omitted, not sent as "": the contract types both as optional, and an empty string is a
    // value the user chose to leave blank — which the prompt builder would then have to
    // re-interpret as absence. One meaning of "not filled in", decided here.
    await createGeneration('Тема', 'doklad', {
      ...EMPTY_PARAMETERS,
      requirements: value,
      extraWishes: value,
    })

    const body = postedBody()
    expect('requirements' in body).toBe(false)
    expect('extra_wishes' in body).toBe(false)
  })

  it('still sends the previous default when the caller supplies nothing', async () => {
    // The compatibility claim: a call site that has not been updated must keep asking for what
    // it always asked for rather than sending an undefined volume the server refuses.
    await createGeneration('Тема', 'doklad')

    expect(postedBody().volume_pages).toBe(EMPTY_PARAMETERS.volumePages)
  })
})
