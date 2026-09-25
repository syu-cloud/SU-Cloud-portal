import {
  type FormEvent,
  useState,
} from 'react'

import {
  type FlavorItem,
  type ImageItem,
} from '../api/catalog'
import { type VmCreateResponse } from '../api/vms'

type VmCreatePanelProps = {
  images: ImageItem[]
  flavor: FlavorItem | null
  freeSlots: number | null
  loading: boolean
  error: string | null
  creating: boolean
  createError: string | null
  createResult: VmCreateResponse | null
  onCreate: (
    count: number,
    imageId: string,
  ) => Promise<boolean>
}

export function VmCreatePanel({
  images,
  flavor,
  freeSlots,
  loading,
  error,
  creating,
  createError,
  createResult,
  onCreate,
}: VmCreatePanelProps) {
  const [selectedImageId, setSelectedImageId] = useState('')
  const [countInput, setCountInput] = useState('1')
  const [confirming, setConfirming] = useState(false)

  const count = Number(countInput)

  const validCount = (
    Number.isInteger(count)
    && count >= 1
    && freeSlots !== null
    && count <= freeSlots
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
    && freeSlots !== null
    && freeSlots > 0
    && validCount
  )

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
    }
  }

  if (confirming && selectedImage && flavor) {
    return (
      <section>
        <h2>VM 생성 확인</h2>

        <p>이미지: {selectedImage.name}</p>
        <p>생성 수량: {count}대</p>

        <p>
          Flavor: {flavor.name}
          {' · '}
          vCPU {flavor.vcpus}
          {' · '}
          RAM {flavor.ram_mb}MB
          {' · '}
          Disk {flavor.disk_gb}GB
        </p>

        {createError && (
          <>
            <p>VM 생성 요청에 실패했습니다.</p>
            <p>{createError}</p>
          </>
        )}

        <button
          type="button"
          onClick={() => setConfirming(false)}
          disabled={creating}
        >
          뒤로
        </button>

        <button
          type="button"
          onClick={() => void handleCreate()}
          disabled={creating}
        >
          {creating ? '생성 요청 중...' : 'VM 생성'}
        </button>
      </section>
    )
  }

  return (
    <section>
      <h2>VM 생성</h2>

      {freeSlots !== null && (
        <p>현재 생성 가능한 여유 슬롯: {freeSlots}대</p>
      )}

      {loading && <p>생성 옵션 조회 중...</p>}

      {error && (
        <>
          <p>생성 옵션 조회에 실패했습니다.</p>
          <p>{error}</p>
        </>
      )}

      {createResult && (
        <p>
          최근 생성 요청:
          {' '}
          요청 {createResult.requested_count}대 /
          {' '}
          접수 {createResult.accepted_count}대
        </p>
      )}

      {createError && !confirming && (
        <>
          <p>최근 생성 요청에 실패했습니다.</p>
          <p>{createError}</p>
        </>
      )}

      {!loading && !error && (
        <form onSubmit={handleConfirm}>
          <div>
            <label htmlFor="vm-image">이미지</label>
            <select
              id="vm-image"
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

          <div>
            <label htmlFor="vm-count">생성 수량</label>
            <input
              id="vm-count"
              type="number"
              min="1"
              max={freeSlots ?? undefined}
              step="1"
              value={countInput}
              onChange={(event) => {
                setCountInput(event.target.value)
              }}
              disabled={
                freeSlots === null
                || freeSlots === 0
                || creating
              }
            />
          </div>

          {flavor && (
            <p>
              Flavor: {flavor.name}
              {' · '}
              vCPU {flavor.vcpus}
              {' · '}
              RAM {flavor.ram_mb}MB
              {' · '}
              Disk {flavor.disk_gb}GB
            </p>
          )}

          {!flavor && (
            <p>사용 가능한 Flavor 정보를 확인할 수 없습니다.</p>
          )}

          {freeSlots === 0 && (
            <p>
              현재 여유 슬롯이 없어 VM을 추가로 생성할 수 없습니다.
            </p>
          )}

          {freeSlots !== null && freeSlots > 0 && !validCount && (
            <p>
              생성 수량은 1대 이상, 현재 여유 슬롯 이하로 입력해야 합니다.
            </p>
          )}

          <button
            type="submit"
            disabled={!canProceed || creating}
          >
            확인 단계로
          </button>
        </form>
      )}
    </section>
  )
}
