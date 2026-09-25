import { apiRequest } from './client'

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

export type VmListParams = {
  q?: string
  status?: VmStatus
}

export function getVms(
  params: VmListParams = {},
): Promise<VmListResponse> {
  const query = new URLSearchParams()

  if (params.q) {
    query.set('q', params.q)
  }

  if (params.status) {
    query.set('status', params.status)
  }

  const queryString = query.toString()
  const path = queryString
    ? `/api/v1/vms?${queryString}`
    : '/api/v1/vms'

  return apiRequest<VmListResponse>(path)
}
