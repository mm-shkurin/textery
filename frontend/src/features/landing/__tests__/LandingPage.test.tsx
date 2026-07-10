import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { LandingPage } from '../components/LandingPage'

describe('LandingPage', () => {
  it('should display the hero heading', () => {
    render(<LandingPage />)

    // toHaveTextContent does a substring `includes()` check (see jest-dom matchers-*.js
    // `matches()`), not exact equality -- asserting on `.textContent` with `toBe` instead
    // so a partial-text render (e.g. missing a word) fails the test.
    expect(screen.getByTestId('hero-heading').textContent).toBe('Word онлайн')
  })
})
