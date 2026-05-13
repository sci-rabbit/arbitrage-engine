import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { authApi } from '../api/auth'

type Status = 'verifying' | 'success' | 'error'

export function VerifyEmail() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const [status, setStatus] = useState<Status>('verifying')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      return
    }
    authApi
      .verifyEmail(token)
      .then(() => setStatus('success'))
      .catch(() => setStatus('error'))
  }, [token])

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-bg-base px-4">
      <div className="w-full max-w-sm text-center">
        {status === 'verifying' && (
          <>
            <div className="mb-4 flex justify-center">
              <div className="h-10 w-10 animate-spin rounded-full border-2 border-border border-t-primary" />
            </div>
            <p className="text-sm text-gray-400">Verifying your email…</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="mb-4 flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
                <svg className="h-8 w-8 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
            </div>
            <h2 className="text-xl font-bold text-white">Email verified!</h2>
            <p className="mt-2 text-sm text-gray-400">Your account is active. Choose a plan to get started.</p>
            <Link
              to="/pricing"
              className="mt-6 inline-block rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
            >
              View plans
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="mb-4 flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-danger/10">
                <svg className="h-8 w-8 text-danger" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </div>
            </div>
            <h2 className="text-xl font-bold text-white">Verification failed</h2>
            <p className="mt-2 text-sm text-gray-400">
              The link may have expired or already been used.
            </p>
            <Link
              to="/login"
              className="mt-6 inline-block text-sm text-primary hover:underline"
            >
              Back to sign in
            </Link>
          </>
        )}
      </div>
    </div>
  )
}