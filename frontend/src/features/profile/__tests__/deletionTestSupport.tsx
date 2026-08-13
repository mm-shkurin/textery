import type { ReactElement } from 'react'
import { render } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

// The deletion tests are about WHERE the user ends up as much as about what is sent, so they need
// a router with somewhere to end up. The landing page itself is not rendered — it would drag the
// whole flow in — but the route it occupies is, with a marker that says the navigation happened.
export const LANDING_MARKER = 'landing-reached'

export function renderAtProfile(screen: ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/profile']}>
      <Routes>
        <Route path="/profile" element={screen} />
        <Route path="/" element={<div data-testid={LANDING_MARKER} />} />
      </Routes>
    </MemoryRouter>,
  )
}
