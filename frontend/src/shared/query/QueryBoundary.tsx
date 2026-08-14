import type { ReactNode } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './queryClient'

/**
 * Makes the shared cache available to everything below it.
 *
 * Mounted at the app root AND by each screen that reads through the cache. The repetition is
 * deliberate: nesting a provider that carries the SAME client changes nothing at runtime, and it
 * means a screen can be rendered on its own — by a test, by a future route, by a storybook — and
 * still work. The alternative is a component that silently requires an ancestor it never names.
 */
export function QueryBoundary({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
