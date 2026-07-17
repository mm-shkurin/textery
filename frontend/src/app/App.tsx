import { BrowserRouter, Route, Routes, useInRouterContext } from 'react-router-dom'
import { RegisterForm } from '../features/auth/components/RegisterForm'
import { LoginForm } from '../features/auth/components/LoginForm'
import { VerifyCodeForm } from '../features/auth/components/VerifyCodeForm'
import { DocumentGenerationFlow } from './DocumentGenerationFlow'

function AppRoutes() {
  return (
    <Routes>
      <Route path="/register" element={<RegisterForm />} />
      <Route path="/login" element={<LoginForm />} />
      <Route path="/verify" element={<VerifyCodeForm />} />
      <Route path="/*" element={<DocumentGenerationFlow />} />
    </Routes>
  )
}

// Renders its own BrowserRouter when not already inside one (production entry
// via main.tsx omits an outer Router), but defers to an existing Router
// context when a test wraps App in MemoryRouter directly.
function App() {
  const isInsideRouter = useInRouterContext()

  if (isInsideRouter) {
    return <AppRoutes />
  }

  return (
    <BrowserRouter>
      <AppRoutes />
    </BrowserRouter>
  )
}

export default App
