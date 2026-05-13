import { useState, type FormEvent } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '../api/auth'

export function ResetPassword() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const navigate = useNavigate()
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [validationErr, setValidationErr] = useState('')

  const { mutate, isPending, error, isSuccess } = useMutation({
    mutationFn: () => authApi.resetPassword(token, password),
    onSuccess: () => setTimeout(() => navigate('/login'), 2000),
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (password !== confirm) {
      setValidationErr('Passwords do not match.')
      return
    }
    setValidationErr('')
    mutate()
  }

  if (isSuccess) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-bg-base px-4">
        <div className="w-full max-w-sm text-center">
          <div className="mb-4 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
              <svg className="h-8 w-8 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
          <h2 className="text-xl font-bold text-white">Password updated!</h2>
          <p className="mt-2 text-sm text-gray-400">Redirecting to sign in…</p>
        </div>
      </div>
    )
  }

  const errMsg = (() => {
    if (validationErr) return validationErr
    if (!error) return null
    const status = (error as { response?: { status: number } }).response?.status
    if (status === 400) return 'Reset link is invalid or has expired.'
    return 'Something went wrong. Please try again.'
  })()

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-bg-base px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white">Set new password</h1>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-gray-400">New password</span>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-border bg-bg-surface px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:border-primary focus:outline-none"
              placeholder="Min. 8 characters"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-gray-400">Confirm password</span>
            <input
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="rounded-lg border border-border bg-bg-surface px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:border-primary focus:outline-none"
              placeholder="Repeat password"
            />
          </label>

          {errMsg && (
            <p className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-sm text-danger">
              {errMsg}
            </p>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {isPending ? 'Saving…' : 'Set new password'}
          </button>
        </form>

        <p className="mt-6 text-center">
          <Link to="/login" className="text-sm text-primary hover:underline">
            Back to sign in
          </Link>
        </p>
      </div>
    </div>
  )
}