import { type FormEvent, useState } from 'react'

type LoginFormProps = {
  error: string | null
  submitting: boolean
  onSubmit: (
    username: string,
    password: string,
  ) => Promise<void>
}

export function LoginForm({
  error,
  submitting,
  onSubmit,
}: LoginFormProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await onSubmit(username, password)
  }

  return (
    <div className="login-card card">
      <h1>로그인</h1>

      <form
        className="login-form"
        onSubmit={handleSubmit}
      >
        <div className="field">
          <label htmlFor="username">아이디</label>

          <input
            className="input"
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={submitting}
            required
          />
        </div>

        <div className="field">
          <label htmlFor="password">비밀번호</label>

          <input
            className="input"
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={submitting}
            required
          />
        </div>

        {error && (
          <p
            className="error-text"
            role="alert"
          >
            {error}
          </p>
        )}

        <button
          className="button button-primary login-button"
          type="submit"
          disabled={submitting}
        >
          {submitting ? '로그인 중...' : '로그인'}
        </button>
      </form>
    </div>
  )
}
