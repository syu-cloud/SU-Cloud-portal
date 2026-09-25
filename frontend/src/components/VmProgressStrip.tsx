type VmProgressStripProps = {
  activeCount: number
  provisioningCount: number
  failedCount: number
}

export function VmProgressStrip({
  activeCount,
  provisioningCount,
  failedCount,
}: VmProgressStripProps) {
  const total = (
    activeCount
    + provisioningCount
    + failedCount
  )

  if (provisioningCount === 0 || total === 0) {
    return null
  }

  return (
    <section className="progress-strip">
      <div className="progress-strip-header">
        <span className="live-label">
          <span className="live-dot" />
          생성 중
        </span>

        <span className="muted">
          완료 {activeCount}
          {' · '}
          진행 {provisioningCount}
          {' · '}
          실패 {failedCount}
        </span>
      </div>

      <div className="progress-bar">
        <span
          className="progress-active"
          style={{
            width: `${(activeCount / total) * 100}%`,
          }}
        />

        <span
          className="progress-running"
          style={{
            width: `${(provisioningCount / total) * 100}%`,
          }}
        />

        <span
          className="progress-failed"
          style={{
            width: `${(failedCount / total) * 100}%`,
          }}
        />
      </div>
    </section>
  )
}
