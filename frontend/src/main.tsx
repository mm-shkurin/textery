import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { App } from './app/App.tsx'
import { initTheme } from './shared/theme/themeStore'
import { browserDocument } from './shared/lib/browser'
import { QueryBoundary } from './shared/query/QueryBoundary'
import { trackSiteVisit } from './shared/analytics/trackers'

// The safety net, not the mechanism. The theme is already on <html> by the time this runs — the
// inline script in index.html put it there before the first paint. This re-asserts it for the one
// case that script cannot cover: a Content-Security-Policy that forbids inline script, which
// would otherwise leave the app permanently light with no error anywhere.
//
// Before `render`, so it still cannot cause a repaint of anything React has drawn.
initTheme()

// One site visit per page load, and the first-touch campaign freeze that rides with it.
//
// HERE rather than in a component effect, for two reasons. StrictMode double-invokes effects and
// genuinely re-runs them, so an effect-based visit is two visits in development and a habit of
// looking at a doubled number. And the URL's `utm_*` are only reliably readable before the router
// mounts and starts rewriting the location — a freeze that runs after it can miss the very
// parameters it exists to capture.
//
// Before `render`, and it cannot delay it: `trackSiteVisit` returns void and the request is
// fire-and-forget, so a backend that is down costs the visitor nothing.
trackSiteVisit()

const host = browserDocument()?.getElementById('root')
if (!host) throw new Error('Не найден корневой элемент #root — проверьте index.html.')

createRoot(host).render(
  <StrictMode>
    <QueryBoundary>
      <App />
    </QueryBoundary>
  </StrictMode>,
)
