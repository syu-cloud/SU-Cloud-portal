import {
  type FormEvent,
  useState,
} from 'react'

import {
  type FlavorItem,
  type ImageItem,
} from '../api/catalog'
import { ModalDialog } from './ModalDialog'

type SlotSummary = {
  taken: number
  free: number
  total: number
}

// 기존 Portal UI와 표시를 맞추기 위한 임시 값.
// TODO: REST API contract에 security group 정보가 추가되면 응답값으로 교체한다.
const SECURITY_GROUP_LABEL = 'default'

type VmCreatePanelProps = {
  open: boolean
  onClose: () => void
  images: ImageItem[]
  flavor: FlavorItem | null
  slots: SlotSummary | null
  loading: boolean
  error: string | null
  creating: boolean
  createError: string | null
  onCreate: (
    count: number,
    imageId: string,
  ) => Promise<boolean>
}

function formatRam(ramMb: number) {
  if (ramMb % 1024 === 0) {
    return `${ramMb / 1024}GB`
  }

  return `${ramMb}MB`
}

export function VmCreatePanel({
  open,
  onClose,
  images,
  flavor,
  slots,
  loading,
  error,
  creating,
  createError,
  onCreate,
}: VmCreatePanelProps) {
  const [selectedImageId, setSelectedImageId] = useState('')
  const [countInput, setCountInput] = useState('1')
  const [confirming, setConfirming] = useState(false)

  const count = Number(countInput)

  const validCount = (
    Number.isInteger(count)
    && count >= 1
    && slots !== null
    && count <= slots.free
  )

  const effectiveImageId = (
    images.some((image) => image.id === selectedImageId)
      ? selectedImageId
      : images[0]?.id ?? ''
  )

  const selectedImage = images.find(
    (image) => image.id === effectiveImageId,
  ) ?? null

  const canProceed = (
    !loading
    && !error
    && selectedImage !== null
    && flavor !== null
    && slots !== null
    && slots.free > 0
    && validCount
  )

  function handleClose() {
    if (creating) {
      return
    }

    setConfirming(false)
    onClose()
  }

  function handleConfirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!canProceed) {
      return
    }

    setConfirming(true)
  }

  async function handleCreate() {
    if (!selectedImage || !validCount || creating) {
      return
    }

    const created = await onCreate(
      count,
      selectedImage.id,
    )

    if (created) {
      setConfirming(false)
      onClose()
    }
  }

  function changeCount(delta: number) {
    const current = Number(countInput) || 1
    const maximum = slots?.free ?? current

    const next = Math.max(
      1,
      Math.min(maximum, current + delta),
    )

    setCountInput(String(next))
  }

  if (!open) {
    return null
  }

  const projectedTaken = (
    slots && validCount
      ? slots.taken + count
      : slots?.taken ?? 0
  )

  const projectedFree = (
    slots && validCount
      ? slots.free - count
      : slots?.free ?? 0
  )

  return (
    <ModalDialog
      title={confirming ? 'VM 생성 확인' : 'VM 생성'}
      onClose={handleClose}
      closeDisabled={creating}
    >

        {confirming && selectedImage && flavor ? (
          <>
            <p className="confirm-message">
              <strong>{count}대</strong>를 생성합니다.
              계속할까요?
            </p>

            <dl className="confirm-list">
              <div>
                <dt>이미지</dt>
                <dd>{selectedImage.name}</dd>
              </div>
              <div>
                <dt>Flavor</dt>
                <dd>
                  {flavor.name}
                  {' · '}
                  {flavor.vcpus}vCPU
                  {' · '}
                  {formatRam(flavor.ram_mb)}
                  {' · '}
                  {flavor.disk_gb}GB
                </dd>
              </div>
            </dl>

            {createError && (
              <div
                className="flash flash-error"
                role="alert"
              >
                <strong>VM 생성 요청에 실패했습니다.</strong>
                <span>{createError}</span>
              </div>
            )}

            <div className="modal-actions">
              <button
                className="button button-ghost"
                type="button"
                onClick={() => setConfirming(false)}
                disabled={creating}
              >
                이전
              </button>

              <button
                className="button button-primary"
                type="button"
                onClick={() => void handleCreate()}
                disabled={creating}
              >
                {creating ? '생성 요청 중...' : '생성 시작'}
              </button>
            </div>
          </>
        ) : (
          <>
            {loading && (
              <div className="flash flash-info">
                생성 옵션을 조회하고 있습니다.
              </div>
            )}

            {error && (
              <div
                className="flash flash-error"
                role="alert"
              >
                <strong>생성 옵션 조회에 실패했습니다.</strong>
                <span>{error}</span>
              </div>
            )}

            {createError && (
              <div
                className="flash flash-error"
                role="alert"
              >
                <strong>최근 생성 요청에 실패했습니다.</strong>
                <span>{createError}</span>
              </div>
            )}

            {!loading && !error && (
              <form onSubmit={handleConfirm}>
                <p className="section-label">VM 생성 설정</p>

                <div className="settings-list">
                  <div className="setting-row">
                    <span className="setting-icon">I</span>
                    <span className="setting-name">image</span>

                    <select
                      className="input setting-control"
                      value={effectiveImageId}
                      onChange={(event) => {
                        setSelectedImageId(event.target.value)
                      }}
                      disabled={images.length === 0}
                    >
                      {images.length === 0 && (
                        <option value="">
                          사용 가능한 이미지 없음
                        </option>
                      )}

                      {images.map((image) => (
                        <option
                          key={image.id}
                          value={image.id}
                        >
                          {image.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="setting-row">
                    <span className="setting-icon">F</span>
                    <span className="setting-name">flavor</span>
                    <span className="setting-value">
                      {flavor
                        ? `${flavor.name} · ${flavor.vcpus}vCPU · ${formatRam(flavor.ram_mb)}`
                        : '—'}
                    </span>
                  </div>

                  <div className="setting-row">
                    <span className="setting-icon">D</span>
                    <span className="setting-name">disk</span>
                    <span className="setting-value">
                      {flavor ? `${flavor.disk_gb}GB` : '—'}
                    </span>
                  </div>

                  <div className="setting-row">
                    <span className="setting-icon">S</span>
                    <span className="setting-name">보안그룹</span>
                    <span className="setting-value">
                      {SECURITY_GROUP_LABEL}
                    </span>
                  </div>
                </div>

                {slots && (
                  <>
                    <p className="section-label usage-label">
                      여유분
                    </p>

                    <div className="usage-summary">
                      <span />
                      <span>
                        <strong>{slots.taken}</strong> 사용
                        {' · '}
                        <strong>{slots.free}</strong> 여유
                        {' / '}
                        최대 {slots.total}
                      </span>
                    </div>

                    <div className="usage-bar">
                      <span
                        style={{
                          width: slots.total > 0
                            ? `${(slots.taken / slots.total) * 100}%`
                            : '0%',
                        }}
                      />
                    </div>
                  </>
                )}

                <p className="section-label count-label">
                  생성 개수
                </p>

                <div className="stepper">
                  <button
                    type="button"
                    onClick={() => changeCount(-1)}
                    disabled={creating}
                  >
                    −
                  </button>

                  <input
                    id="vm-count"
                    type="number"
                    min="1"
                    max={slots?.free ?? undefined}
                    step="1"
                    value={countInput}
                    onChange={(event) => {
                      setCountInput(event.target.value)
                    }}
                    disabled={
                      slots === null
                      || slots.free === 0
                      || creating
                    }
                  />

                  <button
                    type="button"
                    onClick={() => changeCount(1)}
                    disabled={creating}
                  >
                    +
                  </button>
                </div>

                {slots && validCount && (
                  <p className="count-preview">
                    생성 후 {projectedTaken}개 사용
                    {' · '}
                    여유 {projectedFree}
                  </p>
                )}

                {slots && slots.free === 0 && (
                  <p className="error-text">
                    현재 여유 슬롯이 없습니다.
                  </p>
                )}

                {slots && slots.free > 0 && !validCount && (
                  <p className="error-text">
                    생성 수량은 1대 이상, 여유 슬롯 이하로 입력해야 합니다.
                  </p>
                )}

                <div className="modal-actions">
                  <button
                    className="button button-ghost"
                    type="button"
                    onClick={handleClose}
                  >
                    취소
                  </button>

                  <button
                    className="button button-primary"
                    type="submit"
                    disabled={!canProceed || creating}
                  >
                    VM {validCount ? count : 0}개 생성
                  </button>
                </div>
              </form>
            )}
          </>
        )}
    </ModalDialog>
  )
}
