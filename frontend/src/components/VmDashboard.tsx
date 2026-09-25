import { useEffect, useState } from 'react'

import { ApiError } from '../api/client'
import {
  getVms,
  type VmListResponse,
  type VmStatus,
} from '../api/vms'
import { VmList } from './VmList'

const VM_POLL_INTERVAL_MS = 5000

type VmDashboardProps = {
  onUnauthorized: () => void
}

export function VmDashboard({
  onUnauthorized,
}: VmDashboardProps) {
  const [vmData, setVmData] = useState<VmListResponse | null>(null)
  const [vmError, setVmError] = useState<string | null>(null)

  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<VmStatus | ''>('')

  const loading = vmData === null && vmError === null

  useEffect(() => {
    let cancelled = false
    let timerId: number | null = null

    async function pollVms() {
      try {
        const data = await getVms({
          q: searchQuery || undefined,
          status: statusFilter || undefined,
        })

        if (cancelled) {
          return
        }

        setVmData(data)
        setVmError(null)
      } catch (err: unknown) {
        if (cancelled) {
          return
        }

        if (err instanceof ApiError && err.status === 401) {
          setVmData(null)
          setVmError(null)
          onUnauthorized()
          return
        }

        setVmError(
          err instanceof Error
            ? err.message
            : 'Failed to load VM list.',
        )
      }

      if (!cancelled) {
        timerId = window.setTimeout(
          pollVms,
          VM_POLL_INTERVAL_MS,
        )
      }
    }

    void pollVms()

    return () => {
      cancelled = true

      if (timerId !== null) {
        window.clearTimeout(timerId)
      }
    }
  }, [onUnauthorized, searchQuery, statusFilter])

  function handleSearch() {
    setSearchQuery(searchInput.trim())
  }

  return (
    <VmList
      data={vmData}
      error={vmError}
      loading={loading}
      searchInput={searchInput}
      statusFilter={statusFilter}
      onSearchInputChange={setSearchInput}
      onSearch={handleSearch}
      onStatusFilterChange={setStatusFilter}
    />
  )
}
