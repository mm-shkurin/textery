import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useProfileNameForm } from '../hooks/useProfileNameForm'
import { NameRejectedError, saveProfileName } from '../../../shared/identity/api/profileApi'
import { resetIdentity } from '../../../shared/identity/identityStore'
import { NAME_MAX_CODE_POINTS, RAW_NAME_MAX_CODE_POINTS } from '../../../shared/identity/nameValue'
import type { Profile } from '../../../shared/identity/api/profileApi'

// The two length units and the one-PATCH guarantee, which is the whole reason this logic is not
// in the markup. The counter is in CODE POINTS of the NORMALIZED value — the exact units the
// server bounds — and getting either half wrong disables the save button over a name the server
// would have accepted.

vi.mock('../../../shared/identity/api/profileApi', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../../shared/identity/api/profileApi')>()),
  saveProfileName: vi.fn(),
}))

const EMOJI = '\u{1F600}'

function profileNamed(name: string | null): Profile {
  return {
    email: 'ada@example.ru',
    name,
    createdAt: '2025-02-03T09:26:53Z',
    avatarUpdatedAt: null,
    hasPassword: true,
  }
}

function formFor(name: string | null = null) {
  const dirt = { markDirty: vi.fn(), markClean: vi.fn() }
  const rendered = renderHook(() => useProfileNameForm(profileNamed(name), dirt))
  return { ...rendered, dirt }
}

// Every test states the whole behaviour of the client it runs against, rather than overriding a
// shared default. Layering a throwing implementation over a `mockResolvedValue` set in a
// `beforeEach` leaves two implementations on one mock and no way for a reader to tell which one
// answers — and the rejection the losing one produced belongs to nobody, which vitest reports as
// a failure of whichever test happened to be running.
function respondsWith(profile: Profile): void {
  vi.mocked(saveProfileName).mockImplementation(async () => profile)
}

function refusesWith(error: Error): void {
  vi.mocked(saveProfileName).mockImplementation(async () => {
    throw error
  })
}

// Reset, not merely cleared: `clearAllMocks` forgets the calls and KEEPS the implementation.
beforeEach(() => vi.resetAllMocks())

afterEach(() => resetIdentity())

describe('the counter and the two bounds', () => {
  it('starts from the saved name', () => {
    const { result } = formFor('Ада')

    expect(result.current.value).toBe('Ада')
    expect(result.current.changed).toBe(false)
    expect(result.current.canSave).toBe(false)
  })

  it('starts empty when the account has no name', () => {
    expect(formFor(null).result.current.value).toBe('')
  })

  it('counts a name of astral characters in code points, not UTF-16 units', () => {
    // A name of 60 emoji is 60 code points and 120 UTF-16 units. Counting `length` would read
    // 120, redden the counter and disable a save the server answers 200 to.
    const { result } = formFor(null)

    act(() => result.current.change(EMOJI.repeat(NAME_MAX_CODE_POINTS)))

    expect(result.current.count).toBe(NAME_MAX_CODE_POINTS)
    expect(result.current.overLength).toBe(false)
    expect(result.current.canSave).toBe(true)
  })

  it('counts the value after trim and composition, not what was typed', () => {
    // A keyboard that emits NFD sends up to twice the code points for the same visible name.
    const { result } = formFor(null)

    act(() => result.current.change('  ' + 'é'.repeat(NAME_MAX_CODE_POINTS) + '  '))

    expect(result.current.count).toBe(NAME_MAX_CODE_POINTS)
    expect(result.current.canSave).toBe(true)
  })

  it('refuses one character past the stored bound, naming the count', () => {
    const { result } = formFor(null)

    act(() => result.current.change('a'.repeat(NAME_MAX_CODE_POINTS + 1)))

    expect(result.current.overLength).toBe(true)
    expect(result.current.canSave).toBe(false)
    expect(result.current.error).toContain(String(NAME_MAX_CODE_POINTS + 1))
  })

  it('refuses a value past the RAW bound too, under the length message', () => {
    // The raw bound is 256 code points BEFORE normalization, the stored bound 60 after it. NFC
    // compresses by at most 3:1, so anything long enough to trip the raw gate has already
    // tripped the length one — and the length check runs first. The form's own
    // RAW_INPUT_TOO_LARGE_MESSAGE branch is therefore unreachable from this field; the same
    // refusal still reaches the user from the SERVER, where another client can send 300 raw
    // code points and `nameRejectionMessage` renders it.
    const { result } = formFor(null)

    act(() => result.current.change('a'.repeat(RAW_NAME_MAX_CODE_POINTS + 1)))

    expect(result.current.canSave).toBe(false)
    expect(result.current.error).toContain('Имя длиннее')
  })

  it('treats a name differing only in surrounding space as unchanged', () => {
    const { result } = formFor('Ада')

    act(() => result.current.change('  Ада  '))

    expect(result.current.changed).toBe(false)
    expect(result.current.canSave).toBe(false)
  })

  it('treats emptying a set name as a change worth saving', () => {
    const { result } = formFor('Ада')

    act(() => result.current.change(''))

    expect(result.current.changed).toBe(true)
    expect(result.current.canSave).toBe(true)
  })

  it('reports typing as dirty and returning to the saved value as clean', () => {
    const { result, dirt } = formFor('Ада')

    act(() => result.current.change('Грейс'))
    act(() => result.current.change('Ада'))

    expect(dirt.markDirty).toHaveBeenCalledTimes(1)
    expect(dirt.markClean).toHaveBeenCalledTimes(1)
  })

  it('puts the saved value back on cancel and reports the form clean', () => {
    const { result, dirt } = formFor('Ада')
    act(() => result.current.change('Грейс'))

    act(() => result.current.cancel())

    expect(result.current.value).toBe('Ада')
    expect(result.current.error).toBeNull()
    expect(dirt.markClean).toHaveBeenCalled()
  })
})

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
