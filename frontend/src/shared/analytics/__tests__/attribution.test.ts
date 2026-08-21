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
})
