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
import { VmProgressStrip } from './VmProgressStrip'

const VM_POLL_INTERVAL_MS = 5000

type VmDashboardProps = {
  onUnauthorized: () => void
  createDialogOpen: boolean
  onCloseCreateDialog: () => void
}

export function VmDashboard({
  onUnauthorized,
  createDialogOpen,
  onCloseCreateDialog,
}: VmDashboardProps) {
  // ── 화면 · 요청 상태 ──────────────────────────────────────

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
  const [refreshToken, setRefreshToken] = useState(0)

  const loading = vmData === null && vmError === null

  // ── 성공 알림 자동 해제 ──────────────────────────────────

  useEffect(() => {
    if (createResult === null) {
      return
    }

    const timerId = window.setTimeout(() => {
      setCreateResult(null)
    }, 4000)

    return () => {
      window.clearTimeout(timerId)
    }
  }, [createResult])

  useEffect(() => {
    if (reclaimResult === null) {
      return
    }

    const timerId = window.setTimeout(() => {
      setReclaimResult(null)
    }, 4000)

    return () => {
      window.clearTimeout(timerId)
    }
  }, [reclaimResult])

  // ── 생성 옵션 조회 ───────────────────────────────────────

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

  // ── VM 목록 Polling ──────────────────────────────────────

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
  }, [
    onUnauthorized,
    searchQuery,
    statusFilter,
    refreshToken,
  ])

  // ── 사용자 요청 처리 ─────────────────────────────────────

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

      // 기존 Portal의 생성 후 목록 redirect와 동일하게
      // 검색/필터를 초기화하고 polling 계층에 즉시 재조회 신호를 보낸다.
      setSearchInput('')
      setSearchQuery('')
      setStatusFilter('')
      setRefreshToken((current) => current + 1)

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
      setRefreshToken((current) => current + 1)
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
      {createResult && (
        <div className="flash flash-success flash-auto-dismiss">
          최근 생성 요청:
          {' '}
          요청 {createResult.requested_count}대 /
          {' '}
          접수 {createResult.accepted_count}대
        </div>
      )}

      <VmProgressStrip
        activeCount={
          vmData?.summary.status_counts.ACTIVE ?? 0
        }
        provisioningCount={
          vmData?.summary.status_counts.PROVISIONING ?? 0
        }
        failedCount={
          vmData?.summary.status_counts.FAILED ?? 0
        }
      />

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

      <VmCreatePanel
        open={createDialogOpen}
        onClose={onCloseCreateDialog}
        images={images}
        flavor={flavor}
        slots={vmData?.summary.slots ?? null}
        loading={catalogLoading}
        error={catalogError}
        creating={creating}
        createError={createError}
        onCreate={handleCreate}
      />
    </>
  )
}
