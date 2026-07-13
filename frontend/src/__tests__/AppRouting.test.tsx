import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from '../App'

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
    expect(screen.getByTestId('register-confirm-password-input')).toHaveAttribute('type', 'password')
  })
})
