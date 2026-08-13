import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './app/App.tsx'
import { initTheme } from './shared/theme/themeStore'

// The safety net, not the mechanism. The theme is already on <html> by the time this runs — the
// inline script in index.html put it there before the first paint. This re-asserts it for the one
// case that script cannot cover: a Content-Security-Policy that forbids inline script, which
// would otherwise leave the app permanently light with no error anywhere.
//
// Before `render`, so it still cannot cause a repaint of anything React has drawn.
initTheme()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
