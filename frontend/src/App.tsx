import { type FormEvent, useEffect, useState } from 'react'

import {
  getSession,
  loginSession,
  logoutSession,
  type SessionResponse,
} from './api/auth'
import {
  getVms,
  type VmListResponse,
} from './api/vms'

function App() {
  const [session, setSession] = useState<SessionResponse | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loggingIn, setLoggingIn] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)

  const [vmData, setVmData] = useState<VmListResponse | null>(null)
  const [vmError, setVmError] = useState<string | null>(null)

  const authenticated = session?.authenticated === true
  const loadingVms = authenticated && vmData === null && vmError === null

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

  useEffect(() => {
    if (!authenticated) {
      return
    }

    let cancelled = false

    getVms()
      .then((data) => {
        if (!cancelled) {
          setVmData(data)
          setVmError(null)
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setVmError(
            err instanceof Error
              ? err.message
              : 'Failed to load VM list.',
          )
        }
      })

    return () => {
      cancelled = true
    }
  }, [authenticated])

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    setLoginError(null)
    setLoggingIn(true)

    try {
      const data = await loginSession(username, password)
      setSession(data)
      setPassword('')
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

      setVmData(null)
      setVmError(null)
      setUsername('')
      setPassword('')
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

        <h2>VM 현황</h2>

        {loadingVms && <p>VM 목록 조회 중...</p>}

        {vmError && (
          <>
            <p>VM 목록 조회에 실패했습니다.</p>
            <p>{vmError}</p>
          </>
        )}

        {vmData && (
          <>
            <p>
              표시 VM: {vmData.summary.visible_total}대 /
              {' '}슬롯 사용 {vmData.summary.slots.taken} /
              {' '}여유 {vmData.summary.slots.free} /
              {' '}전체 {vmData.summary.slots.total}
            </p>

            <ul>
              {vmData.items.map((vm) => (
                <li key={vm.id}>
                  Slot {vm.slot_id} · {vm.name} · {vm.status}
                  {' · '}
                  {vm.fip ?? '-'}
                  {' · '}
                  {vm.user ?? '-'}
                  {' · '}
                  {vm.image_name ?? '-'}
                </li>
              ))}
            </ul>
          </>
        )}
      </main>
    )
  }

  return (
    <main>
      <h1>SU Cloud Portal</h1>

      <form onSubmit={handleLogin}>
        <div>
          <label htmlFor="username">아이디</label>
          <input
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={loggingIn}
            required
          />
        </div>

        <div>
          <label htmlFor="password">비밀번호</label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={loggingIn}
            required
          />
        </div>

        <button type="submit" disabled={loggingIn}>
          {loggingIn ? '로그인 중...' : '로그인'}
        </button>

        {loginError && <p>{loginError}</p>}
      </form>
    </main>
  )
}

export default App
