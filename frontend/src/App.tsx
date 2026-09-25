import { useCallback, useEffect, useState } from 'react'

import {
  getSession,
  loginSession,
  logoutSession,
  type SessionResponse,
} from './api/auth'
import { LoginForm } from './components/LoginForm'
import { PortalHeader } from './components/PortalHeader'
import { VmDashboard } from './components/VmDashboard'

function App() {
  // ── 세션 · 화면 상태 ──────────────────────────────────────

  const [session, setSession] = useState<SessionResponse | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)

  const [loginError, setLoginError] = useState<string | null>(null)
  const [loggingIn, setLoggingIn] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

  const [createDialogOpen, setCreateDialogOpen] = useState(false)

  // ── 초기 세션 확인 ────────────────────────────────────────

  useEffect(() => {
    let cancelled = false

    getSession()
      .then((data) => {
        if (!cancelled) {
          setSession(data)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setSessionError(
            err instanceof Error
              ? err.message
              : 'Failed to load session.',
          )
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  // ── 인증 동작 ────────────────────────────────────────────

  async function handleLogin(
    username: string,
    password: string,
  ) {
    setLoginError(null)
    setLoggingIn(true)

    try {
      const data = await loginSession(username, password)
      setSession(data)
    } catch (err: unknown) {
      setLoginError(
        err instanceof Error
          ? err.message
          : 'Login failed.',
      )
    } finally {
      setLoggingIn(false)
    }
  }

  async function handleLogout() {
    setSessionError(null)
    setLoggingOut(true)

    try {
      await logoutSession()

      setCreateDialogOpen(false)
      setSession({
        authenticated: false,
        user: null,
      })
    } catch (err: unknown) {
      setSessionError(
        err instanceof Error
          ? err.message
          : 'Logout failed.',
      )
    } finally {
      setLoggingOut(false)
    }
  }

  const handleUnauthorized = useCallback(() => {
    setCreateDialogOpen(false)
    setSession({
      authenticated: false,
      user: null,
    })
  }, [])

  if (sessionError) {
    return (
      <div className="app-shell">
        <PortalHeader />

        <main className="page">
          <div className="card status-card">
            <h1>세션 처리에 실패했습니다.</h1>
            <p className="error-text">{sessionError}</p>
          </div>
        </main>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="app-shell">
        <PortalHeader />

        <main className="page">
          <div className="card status-card">
            <p className="muted">세션 확인 중...</p>
          </div>
        </main>
      </div>
    )
  }

  if (session.authenticated && session.user) {
    return (
      <div className="app-shell">
        <PortalHeader
          username={session.user.username}
          loggingOut={loggingOut}
          onLogout={handleLogout}
          onOpenCreate={() => setCreateDialogOpen(true)}
        />

        <main className="page">
          <VmDashboard
            onUnauthorized={handleUnauthorized}
            createDialogOpen={createDialogOpen}
            onCloseCreateDialog={() => setCreateDialogOpen(false)}
          />
        </main>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <PortalHeader />

      <main className="page login-page">
        <LoginForm
          error={loginError}
          submitting={loggingIn}
          onSubmit={handleLogin}
        />
      </main>
    </div>
  )
}

export default App
