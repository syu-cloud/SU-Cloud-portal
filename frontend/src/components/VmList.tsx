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
import { ReclaimConfirmDialog } from './ReclaimConfirmDialog'
import { VmStatusBadge } from './VmStatusBadge'

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

function formatCreatedAt(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')

  return `${year}-${month}-${day} ${hour}:${minute}`
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
  // ── 선택 · 회수 상태 ──────────────────────────────────────

  const [selectedVmIds, setSelectedVmIds] = useState<number[]>([])
  const [reclaimConfirm, setReclaimConfirm] = useState<
    VmReclaimRequest | null
  >(null)

  const reclaimableItems = (
    data?.items.filter((vm) => vm.can_reclaim) ?? []
  )

  const currentSelectedIds = selectedVmIds.filter(
    (id) => reclaimableItems.some((vm) => vm.id === id),
  )

  // ── 검색 · 필터 · 선택 ──────────────────────────────────

  function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSelectedVmIds([])
    onSearch()
  }

  function changeStatus(value: VmStatus | '') {
    setSelectedVmIds([])
    onStatusFilterChange(value)
  }

  function toggleVm(vmId: number) {
    setSelectedVmIds((current) => (
      current.includes(vmId)
        ? current.filter((id) => id !== vmId)
        : [...current, vmId]
    ))
  }

  // ── 회수 요청 ────────────────────────────────────────────

  function handleSelectedReclaim() {
    if (currentSelectedIds.length === 0 || reclaiming) {
      return
    }

    setReclaimConfirm({
      scope: 'selected',
      vm_ids: [...currentSelectedIds],
    })
  }

  function handleAllReclaim() {
    if (
      data === null
      || data.summary.reclaimable_total === 0
      || reclaiming
    ) {
      return
    }

    setReclaimConfirm({
      scope: 'all',
    })
  }

  async function handleConfirmedReclaim() {
    if (reclaimConfirm === null || reclaiming) {
      return
    }

    const request = reclaimConfirm
    const succeeded = await onReclaim(request)

    if (succeeded && request.scope === 'selected') {
      setSelectedVmIds([])
    }

    setReclaimConfirm(null)
  }

  // ── 조회 상태별 화면 ─────────────────────────────────────

  if (loading) {
    return (
      <div className="card loading-card">
        VM 목록 조회 중...
      </div>
    )
  }

  if (error && !data) {
    return (
      <div
        className="flash flash-error"
        role="alert"
      >
        <strong>VM 목록 조회에 실패했습니다.</strong>
        <span>{error}</span>
      </div>
    )
  }

  if (data && data.summary.visible_total === 0) {
    return (
      <>
        {error && (
          <div
            className="flash flash-error"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="card empty-card">
          <div className="empty-icon">VM</div>
          <h2>아직 생성된 VM이 없어요</h2>
          <p>
            우측 상단의 VM 생성 버튼에서 새 VM을 생성할 수 있습니다.
          </p>
        </div>
      </>
    )
  }

  return (
    <>
      <section className="card control-card">
        <div className="control-top">
          <div className="status-chips">
            <button
              className={`chip ${statusFilter === '' ? 'active' : ''}`}
              type="button"
              onClick={() => changeStatus('')}
            >
              전체
              <strong>{data?.summary.visible_total ?? 0}</strong>
            </button>

            <button
              className={`chip ${statusFilter === 'ACTIVE' ? 'active' : ''}`}
              type="button"
              onClick={() => changeStatus('ACTIVE')}
            >
              ACTIVE
              <strong>{data?.summary.status_counts.ACTIVE ?? 0}</strong>
            </button>

            <button
              className={`chip ${statusFilter === 'PROVISIONING' ? 'active' : ''}`}
              type="button"
              onClick={() => changeStatus('PROVISIONING')}
            >
              PROVISIONING
              <strong>{data?.summary.status_counts.PROVISIONING ?? 0}</strong>
            </button>

            <button
              className={`chip ${statusFilter === 'DELETING' ? 'active' : ''}`}
              type="button"
              onClick={() => changeStatus('DELETING')}
            >
              DELETING
              <strong>{data?.summary.status_counts.DELETING ?? 0}</strong>
            </button>

            <button
              className={`chip ${statusFilter === 'FAILED' ? 'active' : ''}`}
              type="button"
              onClick={() => changeStatus('FAILED')}
            >
              FAILED
              <strong>{data?.summary.status_counts.FAILED ?? 0}</strong>
            </button>
          </div>

          <div className="control-actions">
            <span className="slot-summary">
              여유 슬롯
              {' '}
              {data?.summary.slots.free ?? 0}
              {' / '}
              {data?.summary.slots.total ?? 0}
            </span>

            <button
              className="button button-ghost button-danger"
              type="button"
              disabled={
                data === null
                || data.summary.reclaimable_total === 0
                || reclaiming
              }
              onClick={handleAllReclaim}
            >
              {reclaiming ? '처리 중...' : '전체 회수'}
            </button>
          </div>
        </div>

        <form
          className="search-row"
          onSubmit={handleSearch}
        >
          <input
            className="input"
            id="vm-search"
            type="search"
            aria-label="VM 검색"
            placeholder="이름 / FIP / 계정 / 슬롯 번호 검색"
            value={searchInput}
            onChange={(event) => onSearchInputChange(event.target.value)}
          />

          <button
            className="button button-ghost"
            type="submit"
          >
            검색
          </button>
        </form>
      </section>

      {reclaimResult && (
        <div
          className={
            reclaimResult.summary.rejected > 0
              ? 'flash flash-warning flash-auto-dismiss'
              : 'flash flash-success flash-auto-dismiss'
          }
        >
          최근 회수 요청:
          {' '}
          요청 {reclaimResult.summary.requested}건 /
          {' '}
          처리 {reclaimResult.summary.accepted}건 /
          {' '}
          거절 {reclaimResult.summary.rejected}건
        </div>
      )}

      {reclaimError && (
        <div
          className="flash flash-error"
          role="alert"
        >
          <strong>VM 회수 요청에 실패했습니다.</strong>
          <span>{reclaimError}</span>
        </div>
      )}

      {error && (
        <div
          className="flash flash-error"
          role="alert"
        >
          <strong>VM 목록 갱신에 실패했습니다.</strong>
          <span>{error}</span>
        </div>
      )}

      <section className="card table-card">
        <div className="table-wrap">
          <table className="vm-table">
            <thead>
              <tr>
                <th className="checkbox-column">
                  <span className="sr-only">선택</span>
                </th>
                <th>슬롯</th>
                <th>이름</th>
                <th>이미지</th>
                <th>FIP</th>
                <th>계정</th>
                <th>상태</th>
                <th>생성일</th>
              </tr>
            </thead>

            <tbody>
              {data?.items.map((vm) => (
                <tr key={vm.id}>
                  <td className="checkbox-column">
                    <input
                      type="checkbox"
                      aria-label={`Slot ${vm.slot_id} 선택`}
                      checked={currentSelectedIds.includes(vm.id)}
                      disabled={!vm.can_reclaim || reclaiming}
                      onChange={() => toggleVm(vm.id)}
                    />
                  </td>

                  <td>
                    {String(vm.slot_id).padStart(2, '0')}
                  </td>

                  <td>{vm.name}</td>

                  <td className="muted">
                    {vm.image_name ?? '—'}
                  </td>

                  <td>{vm.fip ?? '—'}</td>

                  <td className="muted">
                    {vm.user ?? '—'}
                  </td>

                  <td className="status-cell">
                    <VmStatusBadge vm={vm} />
                  </td>

                  <td className="muted created-at">
                    {vm.status === 'PROVISIONING'
                      ? '—'
                      : formatCreatedAt(vm.created_at)}
                  </td>
                </tr>
              ))}

              {data && data.items.length === 0 && (
                <tr>
                  <td
                    className="no-results"
                    colSpan={8}
                  >
                    조건에 맞는 VM이 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {currentSelectedIds.length > 0 && (
        <div className="sticky-bar">
          <div className="sticky-bar-inner">
            <span>
              {currentSelectedIds.length}개 선택됨
            </span>

            <div className="sticky-actions">
              <button
                className="button button-ghost"
                type="button"
                onClick={() => setSelectedVmIds([])}
                disabled={reclaiming}
              >
                선택 취소
              </button>

              <button
                className="button button-primary"
                type="button"
                onClick={handleSelectedReclaim}
                disabled={reclaiming}
              >
                {reclaiming ? '처리 중...' : '선택 회수'}
              </button>
            </div>
          </div>
        </div>
      )}

      {reclaimConfirm && (
        <ReclaimConfirmDialog
          mode={reclaimConfirm.scope}
          selectedCount={
            reclaimConfirm.scope === 'selected'
              ? reclaimConfirm.vm_ids.length
              : 0
          }
          submitting={reclaiming}
          onCancel={() => setReclaimConfirm(null)}
          onConfirm={() => void handleConfirmedReclaim()}
        />
      )}
    </>
  )
}
