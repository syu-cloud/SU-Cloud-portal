import { ModalDialog } from './ModalDialog'

type ReclaimConfirmDialogProps = {
  mode: 'selected' | 'all'
  selectedCount?: number
  submitting: boolean
  onCancel: () => void
  onConfirm: () => void
}

export function ReclaimConfirmDialog({
  mode,
  selectedCount = 0,
  submitting,
  onCancel,
  onConfirm,
}: ReclaimConfirmDialogProps) {
  const message = (
    mode === 'selected'
      ? `선택한 ${selectedCount}개를 회수합니다.`
      : '검색·필터와 관계없이 회수 가능한 전체 VM을 회수합니다.'
  )

  return (
    <ModalDialog
      title="VM 회수 확인"
      onClose={onCancel}
      closeDisabled={submitting}
      className="reclaim-modal"
    >
      <div className="reclaim-message">
        <p>{message}</p>
        <p>되돌릴 수 없습니다. 계속할까요?</p>
      </div>

      <div className="modal-actions">
        <button
          className="button button-ghost"
          type="button"
          onClick={onCancel}
          disabled={submitting}
        >
          취소
        </button>

        <button
          className="button button-danger-primary"
          type="button"
          onClick={onConfirm}
          disabled={submitting}
        >
          {submitting ? '처리 중...' : '확인'}
        </button>
      </div>
    </ModalDialog>
  )
}
