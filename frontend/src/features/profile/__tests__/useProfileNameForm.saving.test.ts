import { act } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { NameRejectedError, saveProfileName } from '../../../shared/identity/api/profileApi'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { formFor, profileNamed, refusesWith, respondsWith } from './profileNameFormTestSupport'

// The one-PATCH guarantee and every way a save can be refused. Separated from the counter's suite
// because they exercise the other half of the hook: what the field shows when the server said no,
// and what it shows when the server said nothing at all.

vi.mock('../../../shared/identity/api/profileApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../../shared/identity/api/profileApi')>()),
  saveProfileName: vi.fn(),
}))

// Reset, not merely cleared: `clearAllMocks` forgets the calls and KEEPS the implementation.
beforeEach(() => vi.resetAllMocks())

afterEach(() => resetIdentity())

describe('saving', () => {
  it('sends the normalized value, never what was typed', async () => {
    respondsWith(profileNamed('Грейс'))
    const { result } = formFor('Ада')
    act(() => result.current.change('  Грейс  '))

    await act(async () => await result.current.save())

    expect(saveProfileName).toHaveBeenCalledWith('Грейс')
  })

  it('adopts the value the response carried', async () => {
    respondsWith(profileNamed('Грейс'))
    const { result, dirt } = formFor('Ада')
    act(() => result.current.change('  Грейс  '))

    await act(async () => await result.current.save())

    expect(result.current.value).toBe('Грейс')
    expect(dirt.markClean).toHaveBeenCalled()
  })

  it('empties the field when the response says the name is gone', async () => {
    respondsWith(profileNamed(null))
    const { result } = formFor('Ада')
    act(() => result.current.change(''))

    await act(async () => await result.current.save())

    expect(result.current.value).toBe('')
  })

  it('sends nothing when there is nothing to send', async () => {
    respondsWith(profileNamed('Ада'))
    const { result } = formFor('Ада')

    await act(async () => await result.current.save())

    expect(saveProfileName).not.toHaveBeenCalled()
  })

  it('sends one PATCH for two saves in the same tick', async () => {
    // Double-click and double-Enter are the same event twice; the guard has to be synchronous to
    // see the second one.
    respondsWith(profileNamed('Грейс'))
    const { result } = formFor('Ада')
    act(() => result.current.change('Грейс'))

    await act(async () => {
      await Promise.all([result.current.save(), result.current.save()])
    })

    expect(saveProfileName).toHaveBeenCalledTimes(1)
  })
})

describe('when the save is refused or never answered', () => {
  it('puts a refused name under the field and keeps what was typed', async () => {
    refusesWith(new NameRejectedError('INVALID_NAME', 'ignored'))
    const { result } = formFor('Ада')
    act(() => result.current.change('Грейс'))

    await act(async () => await result.current.save())

    expect(result.current.error).toContain('Такое имя нельзя сохранить')
    expect(result.current.saveFailed).toBe(false)
    expect(result.current.value).toBe('Грейс')
  })

  it('distinguishes the raw-gate refusal from the domain one', async () => {
    refusesWith(new NameRejectedError('NAME_INPUT_TOO_LARGE', 'ignored'))
    const { result } = formFor('Ада')
    act(() => result.current.change('Грейс'))

    await act(async () => await result.current.save())

    expect(result.current.error).toBe('Слишком много введённого текста — сократите имя.')
  })

  it('still says something for a refusal code it does not know', async () => {
    refusesWith(new NameRejectedError('SOMETHING_NEW', 'ignored'))
    const { result } = formFor('Ада')
    act(() => result.current.change('Грейс'))

    await act(async () => await result.current.save())

    expect(result.current.error).toBe('Имя не сохранено — проверьте значение.')
  })

  it('reports a server that never answered as retryable, not as a bad name', async () => {
    refusesWith(new TypeError('Failed to fetch'))
    const { result } = formFor('Ада')
    act(() => result.current.change('Грейс'))

    await act(async () => await result.current.save())

    expect(result.current.saveFailed).toBe(true)
    expect(result.current.error).toBeNull()
    expect(result.current.value).toBe('Грейс')
    expect(result.current.canSave).toBe(true)
  })

  it('clears a previous failure as soon as the value changes again', async () => {
    refusesWith(new TypeError('Failed to fetch'))
    const { result } = formFor('Ада')
    act(() => result.current.change('Грейс'))
    await act(async () => await result.current.save())

    act(() => result.current.change('Грейс Хоппер'))

    expect(result.current.saveFailed).toBe(false)
  })
})
