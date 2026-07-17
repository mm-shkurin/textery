import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../app/App'

describe('App routing', () => {
  // RED: react-router-dom is not installed yet and App has no router/routes.
  // Importing it dynamically here so it.skip actually suppresses resolution;
  // when unskipped without the dependency installed, this rejects with:
  // Error: Failed to resolve import "react-router-dom" from "src/__tests__/AppRouting.test.tsx"
  it('renders RegisterForm at /register', async () => {
    const { MemoryRouter } = await import('react-router-dom')

    render(
      <MemoryRouter initialEntries={['/register']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('register-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('register-password-input')).toHaveAttribute('type', 'password')
    expect(screen.getByTestId('register-confirm-password-input')).toHaveAttribute(
      'type',
      'password',
    )
  })

  // RED: App.tsx has no /login route yet, only /* catch-all rendering
  // DocumentGenerationFlow. Expect a Testing Library "unable to find element"
  // failure, not an import-resolution error (react-router-dom is already used above).
  it('renders LoginForm at /login', async () => {
    const { MemoryRouter } = await import('react-router-dom')

    render(
      <MemoryRouter initialEntries={['/login']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('login-email-input')).toHaveAttribute('type', 'email')
    expect(screen.getByTestId('login-password-input')).toHaveAttribute('type', 'password')
  })

  // RED: App.tsx has no /verify route yet, only /* catch-all rendering
  // DocumentGenerationFlow. Expect a Testing Library "unable to find element"
  // failure, not an import-resolution error (react-router-dom is already used above).
  it('renders VerifyCodeForm at /verify', async () => {
    const { MemoryRouter } = await import('react-router-dom')

    render(
      <MemoryRouter initialEntries={['/verify']}>
        <App />
      </MemoryRouter>,
    )

    for (let index = 0; index < 6; index += 1) {
      const input = screen.getByTestId(`verify-code-input-${index}`)
      expect(input).toHaveAttribute('type', 'text')
      expect(input).toHaveAttribute('inputMode', 'numeric')
      expect(input).toHaveAttribute('maxLength', '1')
    }
    expect(screen.getByTestId('verify-resend-button')).toHaveTextContent(
      'Письмо не пришло? Отправить код повторно',
    )
  })

  it('renders DocumentGenerationFlow landing content for an unmatched path', async () => {
    const { MemoryRouter } = await import('react-router-dom')

    render(
      <MemoryRouter initialEntries={['/does-not-exist']}>
        <App />
      </MemoryRouter>,
    )

    expect(screen.getByTestId('features-primary-cta-button')).toBeInTheDocument()
    expect(screen.queryByTestId('login-email-input')).not.toBeInTheDocument()
    expect(screen.queryByTestId('register-email-input')).not.toBeInTheDocument()
  })
})
