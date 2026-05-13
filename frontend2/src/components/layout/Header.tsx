import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/auth'

export function Header() {
  const { isAuthenticated, hasAccess, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border bg-bg-surface/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4">
        <Link to="/" className="flex items-center gap-2 text-white font-semibold tracking-tight">
          <span className="text-primary text-lg">⬡</span>
          Arbitrage Engine
        </Link>

        <nav className="flex items-center gap-6 text-sm text-gray-400">
          {isAuthenticated && hasAccess && (
            <Link to="/dashboard" className="hover:text-white transition-colors">
              Scanner
            </Link>
          )}
          <Link to="/pricing" className="hover:text-white transition-colors">
            Pricing
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              {!hasAccess && (
                <Link
                  to="/pricing"
                  className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-white hover:bg-primary-hover transition-colors"
                >
                  Upgrade
                </Link>
              )}
              <button
                onClick={handleLogout}
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                Sign Out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm text-gray-400 hover:text-white transition-colors">
                Sign In
              </Link>
              <Link
                to="/register"
                className="rounded-md border border-border bg-bg-elevated px-3 py-1.5 text-sm font-medium text-white hover:bg-bg-card transition-colors"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}