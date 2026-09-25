import {
  type ReactNode,
  useEffect,
  useId,
} from 'react'

type ModalDialogProps = {
  title: string
  children: ReactNode
  onClose: () => void
  closeDisabled?: boolean
  className?: string
}

export function ModalDialog({
  title,
  children,
  onClose,
  closeDisabled = false,
  className = '',
}: ModalDialogProps) {
  const titleId = useId()

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || closeDisabled) {
        return
      }

      onClose()
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [closeDisabled, onClose])

  const modalClassName = (
    className
      ? `modal-card ${className}`
      : 'modal-card'
  )

  return (
    <div
      className="modal-backdrop"
      role="presentation"
    >
      <section
        className={modalClassName}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="modal-header">
          <h2 id={titleId}>
            {title}
          </h2>

          <button
            className="modal-close"
            type="button"
            aria-label="닫기"
            onClick={onClose}
            disabled={closeDisabled}
          >
            ×
          </button>
        </div>

        {children}
      </section>
    </div>
  )
}
