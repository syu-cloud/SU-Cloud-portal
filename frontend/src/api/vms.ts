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

export function getVms(): Promise<VmListResponse> {
  return apiRequest<VmListResponse>('/api/v1/vms')
}
