type PortalHeaderProps = {
  username?: string
  loggingOut?: boolean
  onLogout?: () => void
  onOpenCreate?: () => void
}

export function PortalHeader({
  username,
  loggingOut = false,
  onLogout,
  onOpenCreate,
}: PortalHeaderProps) {
  const authenticated = Boolean(username)

  return (
    <header className="topbar">
      <div className="topbar-inner">
        <div className="brand">
          <img
            className="brand-logo"
            src="/cloudlab-mark.png"
            alt=""
          />

          <strong>SU PORTAL</strong>

          {authenticated && (
            <span className="brand-section">
              VM 관리
            </span>
          )}
        </div>

        {authenticated && username && (
          <div className="topbar-actions">
            <span className="user-area">
              <span className="user-avatar">
                {username.slice(0, 1).toUpperCase()}
              </span>

              {username}
            </span>

            <button
              className="link-button"
              type="button"
              onClick={onLogout}
              disabled={loggingOut}
            >
              {loggingOut ? '로그아웃 중...' : '로그아웃'}
            </button>

            <span className="header-divider" />

            <button
              className="button button-primary"
              type="button"
              onClick={onOpenCreate}
            >
              + VM 생성
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
