export type VmStatus =
  | 'ACTIVE'
  | 'PROVISIONING'
  | 'DELETING'
  | 'FAILED'

export type VmFailure = {
  label: string
  description: string
  detail: string | null
  cleanup_status: string | null
}

export type VmItem = {
  id: number
  slot_id: number
  name: string
  image_name: string | null
  fip: string | null
  user: string | null
  status: VmStatus
  created_at: string
  can_reclaim: boolean
  failure: VmFailure | null
}

export type VmListResponse = {
  items: VmItem[]
  summary: {
    visible_total: number
    status_counts: Record<VmStatus, number>
    slots: {
      taken: number
      free: number
      total: number
    }
  }
}

type ErrorResponse = {
  code?: string
  message?: string
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

export async function getVms(): Promise<VmListResponse> {
  const response = await fetch('/api/v1/vms', {
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
