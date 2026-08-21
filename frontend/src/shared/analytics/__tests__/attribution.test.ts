// First-touch attribution: what gets frozen, what never overwrites it, and what is left open.
import { beforeEach, describe, expect, it } from 'vitest'
import { attributionForRegistration, captureAttribution, forgetAttribution } from '../attribution'

describe('first-touch attribution', () => {
  beforeEach(() => {
    window.localStorage.clear()
    forgetAttribution()
  })

  it('freezes the campaign parameters of the visit that carried them', () => {
    captureAttribution('?utm_source=vk&utm_medium=cpc&utm_campaign=august&utm_term=эссе')

    expect(attributionForRegistration()).toEqual({
      utm_source: 'vk',
      utm_medium: 'cpc',
      utm_campaign: 'august',
      // Decoded, so a multibyte campaign survives the freeze as text rather than as its encoding.
      utm_term: 'эссе',
    })
  })

  it('does not let a later campaign overwrite the first one', () => {
    captureAttribution('?utm_source=vk')

    captureAttribution('?utm_source=newsletter&utm_campaign=september')

    // Last-touch would credit the newsletter for an audience the first link bought.
    expect(attributionForRegistration()).toEqual({ utm_source: 'vk' })
  })

  it('leaves the browser open to a later first touch when a visit carries nothing', () => {
    captureAttribution('')

    captureAttribution('?utm_source=vk')

    // Freezing an empty set on the first direct visit would block attribution permanently for
    // anyone who reaches the landing page before clicking an ad.
    expect(attributionForRegistration()).toEqual({ utm_source: 'vk' })
  })

  it('treats an explicitly empty parameter as an absent one', () => {
    captureAttribution('?utm_source=vk&utm_term=')

    expect(attributionForRegistration()).toEqual({ utm_source: 'vk' })
  })

  it('reports nothing frozen after the account is deleted', () => {
    captureAttribution('?utm_source=vk')

    forgetAttribution()

    // A registration after a deletion must not be attributed to the deleted account's campaign.
    expect(attributionForRegistration()).toEqual({})
  })
  // Everything below reads storage a fresh page load would read — the module caches per load, so
  // `forgetAttribution()` in `beforeEach` is what makes these a second visit rather than the same
  // one continuing.
  it('reads a set frozen by an earlier page load', () => {
    window.localStorage.setItem(
      'textery.analytics.attribution',
      JSON.stringify({ utm_source: 'vk', utm_campaign: 'august' }),
    )

    expect(attributionForRegistration()).toEqual({ utm_source: 'vk', utm_campaign: 'august' })
  })

  it('treats a stored value that is not JSON as nothing frozen, rather than throwing', () => {
    // A corrupt value is ours, so it means a bug or a hand-edit. Letting it throw would take down
    // every registration from that browser for the sake of an analytics field.
    window.localStorage.setItem('textery.analytics.attribution', 'not json{')

    expect(attributionForRegistration()).toEqual({})
  })

  it('treats a stored value that is not an object as nothing frozen', () => {
    window.localStorage.setItem('textery.analytics.attribution', '"vk"')

    expect(attributionForRegistration()).toEqual({})
  })

  it('keeps only the campaign keys, and only the ones carrying text', () => {
    // A hand-edited or future-version blob must not put arbitrary keys on a registration body,
    // and an empty string is the same as an absent parameter everywhere else in this module.
    window.localStorage.setItem(
      'textery.analytics.attribution',
      JSON.stringify({ utm_source: 'vk', utm_term: '', evil: 'x', utm_medium: 7 }),
    )

    expect(attributionForRegistration()).toEqual({ utm_source: 'vk' })
  })

  it('forgets a frozen set, in storage as well as in memory', () => {
    captureAttribution('?utm_source=vk')

    forgetAttribution()

    expect(window.localStorage.getItem('textery.analytics.attribution')).toBeNull()
    expect(attributionForRegistration()).toEqual({})
  })
})
