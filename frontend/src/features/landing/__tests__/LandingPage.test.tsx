import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'

import { LandingPage } from '../components/LandingPage'

describe('LandingPage', () => {
  it('should display the hero heading, subheading, and primary CTA', () => {
    render(<LandingPage />)

    // toHaveTextContent does a substring `includes()` check (see jest-dom matchers-*.js
    // `matches()`), not exact equality -- asserting on `.textContent` with `toBe` instead
    // so a partial-text render (e.g. missing a word) fails the test.
    expect(screen.getByTestId('hero-heading').textContent).toBe('Word онлайн')
    expect(screen.getByTestId('hero-subheading').textContent).toBe(
      'С возможностью генерации через нейросеть Textery AI',
    )
    expect(screen.getByTestId('hero-primary-cta-button').textContent).toBe('Создать генерацию')
  })
})
