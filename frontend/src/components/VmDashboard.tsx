import { useEffect, useState } from 'react'

import {
  getFlavors,
  getImages,
  type FlavorItem,
  type ImageItem,
} from '../api/catalog'
import { ApiError } from '../api/client'
import {
  createVms,
  getVms,
  reclaimVms,
  type VmCreateResponse,
  type VmListResponse,
  type VmReclaimRequest,
  type VmReclaimResponse,
  type VmStatus,
} from '../api/vms'
import { VmCreatePanel } from './VmCreatePanel'
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

  const [images, setImages] = useState<ImageItem[]>([])
  const [flavor, setFlavor] = useState<FlavorItem | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState<string | null>(null)

  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [createResult, setCreateResult] = useState<VmCreateResponse | null>(null)

  const [reclaiming, setReclaiming] = useState(false)
  const [reclaimError, setReclaimError] = useState<string | null>(null)
  const [reclaimResult, setReclaimResult] = useState<VmReclaimResponse | null>(null)

  const [searchInput, setSearchInput] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<VmStatus | ''>('')

  const loading = vmData === null && vmError === null

  useEffect(() => {
    let cancelled = false

    async function loadCatalog() {
      try {
        const [imageData, flavorData] = await Promise.all([
          getImages(),
          getFlavors(),
        ])

        if (cancelled) {
          return
        }

        setImages(imageData.items)
        setFlavor(flavorData.items[0] ?? null)
        setCatalogError(null)
      } catch (err: unknown) {
        if (cancelled) {
          return
        }

        if (err instanceof ApiError && err.status === 401) {
          onUnauthorized()
          return
        }

        setCatalogError(
          err instanceof Error
            ? err.message
            : 'Failed to load VM creation options.',
        )
      } finally {
        if (!cancelled) {
          setCatalogLoading(false)
        }
      }
    }

    void loadCatalog()

    return () => {
      cancelled = true
    }
  }, [onUnauthorized])

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

  async function handleCreate(
    count: number,
    imageId: string,
  ) {
    setCreating(true)
    setCreateError(null)
    setCreateResult(null)

    try {
      const result = await createVms({
        count,
        image_id: imageId,
      })

      setCreateResult(result)
      return true
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized()
        return false
      }

      setCreateError(
        err instanceof Error
          ? err.message
          : 'Failed to create VMs.',
      )

      return false
    } finally {
      setCreating(false)
    }
  }

  async function handleReclaim(
    request: VmReclaimRequest,
  ) {
    setReclaiming(true)
    setReclaimError(null)
    setReclaimResult(null)

    try {
      const result = await reclaimVms(request)

      setReclaimResult(result)
      return true
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized()
        return false
      }

      setReclaimError(
        err instanceof Error
          ? err.message
          : 'Failed to reclaim VMs.',
      )

      return false
    } finally {
      setReclaiming(false)
    }
  }

  return (
    <>
      <VmCreatePanel
        images={images}
        flavor={flavor}
        freeSlots={vmData?.summary.slots.free ?? null}
        loading={catalogLoading}
        error={catalogError}
        creating={creating}
        createError={createError}
        createResult={createResult}
        onCreate={handleCreate}
      />

      <hr />

      <VmList
        data={vmData}
        error={vmError}
        loading={loading}
        searchInput={searchInput}
        statusFilter={statusFilter}
        onSearchInputChange={setSearchInput}
        onSearch={handleSearch}
        onStatusFilterChange={setStatusFilter}
        reclaiming={reclaiming}
        reclaimError={reclaimError}
        reclaimResult={reclaimResult}
        onReclaim={handleReclaim}
      />
    </>
  )
}
