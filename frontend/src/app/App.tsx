import { BrowserRouter, Route, Routes, useInRouterContext } from 'react-router-dom'
import { RegisterForm } from '../features/auth/components/RegisterForm'
import { LoginForm } from '../features/auth/components/LoginForm'
import { VerifyCodeForm } from '../features/auth/components/VerifyCodeForm'
import { OAuthCallback } from '../features/auth/components/OAuthCallback'
import { DocumentGenerationFlow } from './DocumentGenerationFlow'
import { ErrorBoundary } from '../shared/components/ErrorBoundary'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/login" element={<LoginForm />} />
      <Route path="/verify" element={<VerifyCodeForm />} />
      <Route path="/auth/callback" element={<OAuthCallback />} />
      <Route path="/*" element={<DocumentGenerationFlow />} />
    </Routes>
  )
}

// Renders its own BrowserRouter when not already inside one (production entry
// via main.tsx omits an outer Router), but defers to an existing Router
// context when a test wraps App in MemoryRouter directly.
// The editor has its own boundary with a recovery target (back to mode choice). This one is the
// last line: every OTHER route — auth, landing, history — has none, and without it any throw
// there unmounts the tree into a blank white page with no explanation. No recovery button here on
// purpose: at the root there is nowhere safe left to send the user, and a button that re-renders
// the same crash is worse than none.
function App() {
  const isInsideRouter = useInRouterContext()
  const routes = <AppRoutes />

  return (
    <ErrorBoundary title="Что-то пошло не так. Обновите страницу.">
      {isInsideRouter ? routes : <BrowserRouter>{routes}</BrowserRouter>}
    </ErrorBoundary>
  )
}

export default App
