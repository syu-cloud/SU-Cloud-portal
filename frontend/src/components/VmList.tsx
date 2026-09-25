import {
  type FormEvent,
  useState,
} from 'react'

import {
  type VmListResponse,
  type VmReclaimRequest,
  type VmReclaimResponse,
  type VmStatus,
} from '../api/vms'

type VmListProps = {
  data: VmListResponse | null
  error: string | null
  loading: boolean
  searchInput: string
  statusFilter: VmStatus | ''
  reclaiming: boolean
  reclaimError: string | null
  reclaimResult: VmReclaimResponse | null
  onSearchInputChange: (value: string) => void
  onSearch: () => void
  onStatusFilterChange: (value: VmStatus | '') => void
  onReclaim: (
    request: VmReclaimRequest,
  ) => Promise<boolean>
}

export function VmList({
  data,
  error,
  loading,
  searchInput,
  statusFilter,
  reclaiming,
  reclaimError,
  reclaimResult,
  onSearchInputChange,
  onSearch,
  onStatusFilterChange,
  onReclaim,
}: VmListProps) {
  const [selectedVmIds, setSelectedVmIds] = useState<number[]>([])

  const reclaimableItems = (
    data?.items.filter((vm) => vm.can_reclaim) ?? []
  )

  const currentSelectedIds = selectedVmIds.filter(
    (id) => reclaimableItems.some((vm) => vm.id === id),
  )

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSelectedVmIds([])
    onSearch()
  }

  function toggleVm(vmId: number) {
    setSelectedVmIds((current) => (
      current.includes(vmId)
        ? current.filter((id) => id !== vmId)
        : [...current, vmId]
    ))
  }

  async function handleSelectedReclaim() {
    if (currentSelectedIds.length === 0 || reclaiming) {
      return
    }

    if (
      !window.confirm(
        `선택한 ${currentSelectedIds.length}건을 회수 처리하시겠습니까?`,
      )
    ) {
      return
    }

    const succeeded = await onReclaim({
      scope: 'selected',
      vm_ids: currentSelectedIds,
    })

    if (succeeded) {
      setSelectedVmIds([])
    }
  }

  async function handleAllReclaim() {
    if (
      data === null
      || data.summary.visible_total === 0
      || reclaiming
    ) {
      return
    }

    if (
      !window.confirm(
        '검색·필터와 관계없이 현재 회수 가능한 VM 전체를 회수 처리하시겠습니까?',
      )
    ) {
      return
    }

    const succeeded = await onReclaim({
      scope: 'all',
    })

    if (succeeded) {
      setSelectedVmIds([])
    }
  }

  return (
    <>
      <h2>VM 현황</h2>

      <form onSubmit={handleSearch}>
        <label htmlFor="vm-search">검색</label>
        <input
          id="vm-search"
          type="search"
          placeholder="이름, FIP, 계정, Slot"
          value={searchInput}
          onChange={(event) => onSearchInputChange(event.target.value)}
        />
        <button type="submit">조회</button>
      </form>

      <div>
        <label htmlFor="vm-status">상태</label>
        <select
          id="vm-status"
          value={statusFilter}
          onChange={(event) => {
            setSelectedVmIds([])
            onStatusFilterChange(
              event.target.value as VmStatus | '',
            )
          }}
        >
          <option value="">전체</option>
          <option value="ACTIVE">ACTIVE</option>
          <option value="PROVISIONING">PROVISIONING</option>
          <option value="DELETING">DELETING</option>
          <option value="FAILED">FAILED</option>
        </select>
      </div>

      <div>
        <button
          type="button"
          disabled={
            currentSelectedIds.length === 0
            || reclaiming
          }
          onClick={() => void handleSelectedReclaim()}
        >
          {reclaiming ? '처리 중...' : '선택 회수'}
        </button>

        <button
          type="button"
          disabled={
            data === null
            || data.summary.visible_total === 0
            || reclaiming
          }
          onClick={() => void handleAllReclaim()}
        >
          {reclaiming ? '처리 중...' : '전체 회수'}
        </button>
      </div>

      {reclaimResult && (
        <p>
          최근 회수 요청:
          {' '}
          요청 {reclaimResult.summary.requested}건 /
          {' '}
          처리 {reclaimResult.summary.accepted}건 /
          {' '}
          거절 {reclaimResult.summary.rejected}건
        </p>
      )}

      {reclaimError && (
        <>
          <p>VM 회수 요청에 실패했습니다.</p>
          <p>{reclaimError}</p>
        </>
      )}

      {loading && <p>VM 목록 조회 중...</p>}

      {error && (
        <>
          <p>VM 목록 조회에 실패했습니다.</p>
          <p>{error}</p>
        </>
      )}

      {data && (
        <>
          <p>
            전체 관리 VM: {data.summary.visible_total}대 /
            {' '}현재 조회 결과: {data.items.length}대 /
            {' '}슬롯 사용 {data.summary.slots.taken} /
            {' '}여유 {data.summary.slots.free} /
            {' '}전체 {data.summary.slots.total}
          </p>

          <ul>
            {data.items.map((vm) => (
              <li key={vm.id}>
                <input
                  type="checkbox"
                  aria-label={`Slot ${vm.slot_id} 선택`}
                  checked={currentSelectedIds.includes(vm.id)}
                  disabled={!vm.can_reclaim || reclaiming}
                  onChange={() => toggleVm(vm.id)}
                />

                {' '}
                Slot {vm.slot_id} · {vm.name} · {vm.status}
                {' · '}
                {vm.fip ?? '-'}
                {' · '}
                {vm.user ?? '-'}
                {' · '}
                {vm.image_name ?? '-'}

                {vm.failure && (
                  <>
                    {' · '}
                    {vm.failure.label}
                    {' · cleanup='}
                    {vm.failure.cleanup_status ?? 'PENDING'}
                  </>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  )
}
