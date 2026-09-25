import { type VmItem } from '../api/vms'

type VmStatusBadgeProps = {
  vm: VmItem
}

export function VmStatusBadge({
  vm,
}: VmStatusBadgeProps) {
  if (vm.status !== 'FAILED' || !vm.failure) {
    return (
      <span
        className={
          `badge badge-${vm.status.toLowerCase()}`
        }
      >
        {vm.status}
      </span>
    )
  }

  return (
    <span
      className="badge badge-failed fail-hover"
      tabIndex={0}
    >
      FAILED

      <span className="failure-popover">
        <strong>{vm.failure.label}</strong>

        <span>
          {vm.failure.description}
        </span>

        <span className="failure-cleanup">
          cleanup:
          {' '}
          {vm.failure.cleanup_status ?? 'PENDING'}
        </span>

        {vm.failure.detail && (
          <span className="failure-raw">
            {vm.failure.detail}
          </span>
        )}
      </span>
    </span>
  )
}
