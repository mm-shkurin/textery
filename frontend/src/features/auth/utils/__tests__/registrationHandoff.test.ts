import { afterEach, describe, expect, it } from 'vitest'
import {
  consumeRegistration,
  forgetRegistration,
  rememberRegistration,
} from '../registrationHandoff'

describe('registrationHandoff', () => {
  afterEach(() => {
    forgetRegistration()
  })

  it('hands the password to the account it was stored for', () => {
    rememberRegistration('user@example.ru', 'Str0ng!Pass')

    expect(consumeRegistration('user@example.ru')).toBe('Str0ng!Pass')
  })

  // Single-use is the point, not a detail: this is a password held in memory, and the one
  // caller needs it once. A second read means it outlived its reason to exist.
  it('gives the password up only once', () => {
    rememberRegistration('user@example.ru', 'Str0ng!Pass')
    consumeRegistration('user@example.ru')

    expect(consumeRegistration('user@example.ru')).toBeNull()
  })

  // /verify takes its email from router state, which a crafted link controls. Without the
  // email check, a handoff left by one registration could be spent signing into a DIFFERENT
  // account whose code the user happens to hold.
  it('refuses to hand one account password to another account', () => {
    rememberRegistration('victim@example.ru', 'Str0ng!Pass')

    expect(consumeRegistration('attacker@example.ru')).toBeNull()
  })

  it('reports nothing when no registration is pending', () => {
    expect(consumeRegistration('user@example.ru')).toBeNull()
  })

  it('forgets a pending registration on request', () => {
    rememberRegistration('user@example.ru', 'Str0ng!Pass')

    forgetRegistration()

    expect(consumeRegistration('user@example.ru')).toBeNull()
  })
})
