import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { OAuthProviderButtons } from '../OAuthProviderButtons'

// BORN-GREEN GUARD (scenario 2.1). The VK control already ships as a plain <a> to the backend
// start endpoint (built in 1.1 green), so this test is expected to PASS, not fail. It stays
// ENABLED (never describe.skip) so a future regression turns it RED: a VK↔Yandex href swap, an
// href typo, or a switch to a react-router <Link>. A <Link> renders an <a> too, so tagName alone
// cannot catch it — the discriminator is that a <Link> calls preventDefault to client-route,
// while a plain anchor lets the browser do a full-page navigation. We assert defaultPrevented on
// click AND that no background request (fetch) is issued on render or click.
const VK_START = '/api/v1/auth/oauth/vk/start'

describe('OAuthProviderButtons VK button starts the VK handshake', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
      throw new Error('no background request expected during the VK handshake')
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('is a plain anchor to the VK start endpoint that navigates the full page', () => {
    renderWithRouter(<OAuthProviderButtons />)

    const vkButton = screen.getByTestId('oauth-vk-button')
    // Non-vacuity: sanity-check the spy is armed (any fetch would throw), so the "no request"
    // claim below cannot pass by the spy simply never being wired.
    expect(() => globalThis.fetch('/probe')).toThrow('no background request expected')

    expect(vkButton.tagName).toBe('A')
    expect(vkButton).toHaveAttribute('href', VK_START)
    // Guard the swap explicitly: the VK control must NOT point at the Yandex endpoint.
    expect(vkButton).not.toHaveAttribute('href', '/api/v1/auth/oauth/yandex/start')

    // A plain anchor leaves the click's default action intact (browser full-page nav). A
    // react-router <Link> would call preventDefault to intercept and client-route. Assert the
    // discriminating property by name on a cancelable event, not the opaque fireEvent return.
    const click = new MouseEvent('click', { bubbles: true, cancelable: true })
    const dispatched = fireEvent(vkButton, click)
    expect(click.defaultPrevented).toBe(false)
    expect(dispatched).toBe(true)
  })

  it('issues no background request when the VK button is rendered and clicked', () => {
    renderWithRouter(<OAuthProviderButtons />)

    fireEvent.click(screen.getByTestId('oauth-vk-button'))

    expect(globalThis.fetch).not.toHaveBeenCalled()
  })
})
