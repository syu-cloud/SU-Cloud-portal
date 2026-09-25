export type ApiErrorBody = {
  code?: string
  message?: string
  details?: unknown
}

export class ApiError extends Error {
  status: number
  code: string | null
  details: unknown

  constructor(
    status: number,
    code: string | null,
    message: string,
    details: unknown = null,
  ) {
    super(message)

    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

type ApiMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

type ApiRequestOptions = {
  method?: ApiMethod
  body?: unknown
}

const CSRF_COOKIE_NAME = 'suportal_csrftoken'

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

async function readErrorBody(
  response: Response,
): Promise<ApiErrorBody | null> {
  try {
    return (await response.json()) as ApiErrorBody
  } catch {
    return null
  }
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  const method = options.method ?? 'GET'

  const headers: Record<string, string> = {
    Accept: 'application/json',
  }

  let body: string | undefined

  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
    const csrfToken = getCookie(CSRF_COOKIE_NAME)

    if (!csrfToken) {
      throw new ApiError(
        0,
        'CSRF_TOKEN_MISSING',
        'CSRF token is not available.',
      )
    }

    headers['X-CSRFToken'] = csrfToken
  }

  const response = await fetch(path, {
    method,
    headers,
    credentials: 'same-origin',
    body,
  })

  if (!response.ok) {
    const errorBody = await readErrorBody(response)

    throw new ApiError(
      response.status,
      errorBody?.code ?? null,
      errorBody?.message ?? `Request failed (${response.status})`,
      errorBody?.details ?? null,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
