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
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="username">아이디</label>
        <input
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

      <div>
        <label htmlFor="password">비밀번호</label>
        <input
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

      <button type="submit" disabled={submitting}>
        {submitting ? '로그인 중...' : '로그인'}
      </button>

      {error && <p>{error}</p>}
    </form>
  )
}
