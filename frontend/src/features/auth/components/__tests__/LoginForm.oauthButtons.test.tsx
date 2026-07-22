import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithRouter } from '../../../../test/renderWithRouter'
import { LoginForm } from '../LoginForm'

// RED: LoginForm renders email/password + submit + register link only — it has no OAuth
// provider buttons yet. Unskip in green-frontend once oauth-vk-button / oauth-yandex-button
// are added. Currently fails: TestingLibraryElementError: Unable to find an element by:
// [data-testid="oauth-vk-button"] (and the Yandex testid).
describe('LoginForm OAuth provider buttons', () => {
  it('shows a VK ID button distinct from the primary submit button', () => {
    renderWithRouter(<LoginForm />)

    const vkButton = screen.getByTestId('oauth-vk-button')
    // Assert the ACCESSIBLE NAME, not raw textContent: the mockup puts a decorative provider
    // badge ("VK") inside the control, so textContent is "VKВойти через VK ID". The badge must
    // be aria-hidden, making the accessible name exactly the label — this pins the label AND
    // forces the badge to be decorative (green must aria-hide it), matching the mockup.
    expect(screen.getByRole('link', { name: 'Войти через VK ID' })).toBe(vkButton)
    expect(vkButton).not.toBe(screen.getByTestId('login-submit-button'))
  })

  it('shows a Yandex ID button distinct from the primary submit button', () => {
    renderWithRouter(<LoginForm />)

    const yandexButton = screen.getByTestId('oauth-yandex-button')
    // Accessible name excludes the decorative (aria-hidden) "Я" badge — see the VK test.
    expect(screen.getByRole('link', { name: 'Войти через Yandex ID' })).toBe(yandexButton)
    expect(yandexButton).not.toBe(screen.getByTestId('login-submit-button'))
  })

  it('renders both OAuth buttons below the primary submit button', () => {
    renderWithRouter(<LoginForm />)

    const submit = screen.getByTestId('login-submit-button')
    const vkButton = screen.getByTestId('oauth-vk-button')
    const yandexButton = screen.getByTestId('oauth-yandex-button')

    // Three distinct nodes, in this exact DOM order: submit, then VK, then Yandex. Masking to
    // the single flag and asserting equality pins the ordering strictly (not merely truthy).
    expect(vkButton).not.toBe(yandexButton)
    expect(submit.compareDocumentPosition(vkButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
    expect(vkButton.compareDocumentPosition(yandexButton) & Node.DOCUMENT_POSITION_FOLLOWING).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
  })
})
