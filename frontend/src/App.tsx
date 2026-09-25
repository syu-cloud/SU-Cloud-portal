import { useCallback, useEffect, useState } from 'react'

import {
  getSession,
  loginSession,
  logoutSession,
  type SessionResponse,
} from './api/auth'
import { LoginForm } from './components/LoginForm'
import { VmDashboard } from './components/VmDashboard'

function App() {
  const [session, setSession] = useState<SessionResponse | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)

  const [loginError, setLoginError] = useState<string | null>(null)
  const [loggingIn, setLoggingIn] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

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
    setSession({
      authenticated: false,
      user: null,
    })
  }, [])

  if (sessionError) {
    return (
      <main>
        <h1>SU Cloud Portal</h1>
        <p>세션 처리에 실패했습니다.</p>
        <p>{sessionError}</p>
      </main>
    )
  }

  if (!session) {
    return (
      <main>
        <h1>SU Cloud Portal</h1>
        <p>세션 확인 중...</p>
      </main>
    )
  }

  if (session.authenticated && session.user) {
    return (
      <main>
        <h1>SU Cloud Portal</h1>
        <p>{session.user.username} 로그인 상태</p>

        <button
          type="button"
          onClick={handleLogout}
          disabled={loggingOut}
        >
          {loggingOut ? '로그아웃 중...' : '로그아웃'}
        </button>

        <hr />

        <VmDashboard
          onUnauthorized={handleUnauthorized}
        />
      </main>
    )
  }

  return (
    <main>
      <h1>SU Cloud Portal</h1>

      <LoginForm
        error={loginError}
        submitting={loggingIn}
        onSubmit={handleLogin}
      />
    </main>
  )
}

export default App
