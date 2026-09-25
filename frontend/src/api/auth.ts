export type SessionUser = {
  username: string
}

export type SessionResponse = {
  authenticated: boolean
  user: SessionUser | null
}

type ErrorResponse = {
  code?: string
  message?: string
}

function getCookie(name: string): string | null {
  const prefix = `${name}=`

  for (const cookie of document.cookie.split(';')) {
    const value = cookie.trim()

    if (value.startsWith(prefix)) {
      return decodeURIComponent(value.slice(prefix.length))
    }
  }

  return null
}

async function getErrorMessage(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as ErrorResponse

    if (data.message) {
      return data.message
    }
  } catch {
    // JSON 형식이 아닌 오류 응답은 아래 기본 문구를 사용한다.
  }

  return `Request failed (${response.status})`
}

export async function getSession(): Promise<SessionResponse> {
  const response = await fetch('/api/v1/auth/session', {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    credentials: 'same-origin',
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json()
}

export async function loginSession(
  username: string,
  password: string,
): Promise<SessionResponse> {
  const csrfToken = getCookie('suportal_csrftoken')

  if (!csrfToken) {
    throw new Error('CSRF token is not available.')
  }

  const response = await fetch('/api/v1/auth/session', {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'same-origin',
    body: JSON.stringify({
      username,
      password,
    }),
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json()
}

export async function logoutSession(): Promise<void> {
  const csrfToken = getCookie('suportal_csrftoken')

  if (!csrfToken) {
    throw new Error('CSRF token is not available.')
  }

  const response = await fetch('/api/v1/auth/session', {
    method: 'DELETE',
    headers: {
      Accept: 'application/json',
      'X-CSRFToken': csrfToken,
    },
    credentials: 'same-origin',
  })

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }
}
