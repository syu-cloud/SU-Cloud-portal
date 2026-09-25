import { type FormEvent } from 'react'

import {
  type VmListResponse,
  type VmStatus,
} from '../api/vms'

type VmListProps = {
  data: VmListResponse | null
  error: string | null
  loading: boolean
  searchInput: string
  statusFilter: VmStatus | ''
  onSearchInputChange: (value: string) => void
  onSearch: () => void
  onStatusFilterChange: (value: VmStatus | '') => void
}

export function VmList({
  data,
  error,
  loading,
  searchInput,
  statusFilter,
  onSearchInputChange,
  onSearch,
  onStatusFilterChange,
}: VmListProps) {
  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSearch()
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
                Slot {vm.slot_id} · {vm.name} · {vm.status}
                {' · '}
                {vm.fip ?? '-'}
                {' · '}
                {vm.user ?? '-'}
                {' · '}
                {vm.image_name ?? '-'}
              </li>
            ))}
          </ul>
        </>
      )}
    </>
  )
}
