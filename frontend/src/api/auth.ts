import { apiRequest } from './client'

export type SessionUser = {
  username: string
}

export type SessionResponse = {
  authenticated: boolean
  user: SessionUser | null
}

export function getSession(): Promise<SessionResponse> {
  return apiRequest<SessionResponse>(
    '/api/v1/auth/session',
  )
}

export function loginSession(
  username: string,
  password: string,
): Promise<SessionResponse> {
  return apiRequest<SessionResponse>(
    '/api/v1/auth/session',
    {
      method: 'POST',
      body: {
        username,
        password,
      },
    },
  )
}

export function logoutSession(): Promise<void> {
  return apiRequest<void>(
    '/api/v1/auth/session',
    {
      method: 'DELETE',
    },
  )
}
