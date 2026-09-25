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
    reclaimable_total: number
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

export type VmCreateRequest = {
  count: number
  image_id: string
}

export type VmCreateItem = {
  id: number
  slot_id: number
  status: 'PROVISIONING'
}

export type VmCreateResponse = {
  requested_count: number
  accepted_count: number
  items: VmCreateItem[]
}

export function createVms(
  request: VmCreateRequest,
): Promise<VmCreateResponse> {
  return apiRequest<VmCreateResponse>(
    '/api/v1/vms',
    {
      method: 'POST',
      body: request,
    },
  )
}

export type VmReclaimRequest =
  | {
      scope: 'selected'
      vm_ids: number[]
    }
  | {
      scope: 'all'
    }

export type VmReclaimResult = {
  vm_id: number
  accepted: boolean
  code?: 'VM_NOT_FOUND' | 'VM_NOT_RECLAIMABLE'
}

export type VmReclaimResponse = {
  summary: {
    requested: number
    accepted: number
    rejected: number
  }
  results: VmReclaimResult[]
}

export function reclaimVms(
  request: VmReclaimRequest,
): Promise<VmReclaimResponse> {
  return apiRequest<VmReclaimResponse>(
    '/api/v1/vms/reclaim-requests',
    {
      method: 'POST',
      body: request,
    },
  )
}
