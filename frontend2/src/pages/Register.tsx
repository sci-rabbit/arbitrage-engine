import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { authApi } from '../api/auth'
import { useAuthStore } from '../store/auth'

export function Register() {
  const navigate = useNavigate()
  const setTokens = useAuthStore((s) => s.setTokens)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [done, setDone] = useState(false)

  const { mutate, isPending, error } = useMutation({
    mutationFn: () => authApi.register(email, password),
    onSuccess: async () => {
      try {
        const { data } = await authApi.login(email, password)
        setTokens(data.access_token, data.refresh_token)
      } catch {
        // login after register failed — non-critical
      }
      setDone(true)
    },
  })

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    mutate()
  }

  const errMsg = (() => {
    if (!error) return null
    const status = (error as { response?: { status: number } }).response?.status
    if (status === 409) return 'An account with this email already exists.'
    return 'Registration failed. Please try again.'
  })()

  if (done) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-bg-base px-4">
        <div className="w-full max-w-sm text-center">
          <div className="mb-4 flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <svg className="h-8 w-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
          </div>
          <h2 className="text-xl font-bold text-white">Check your email</h2>
          <p className="mt-3 text-sm text-gray-400">
            We sent a verification link to <span className="text-white">{email}</span>.
            Click it to activate your account.
          </p>
          <button
            onClick={() => navigate('/pricing')}
            className="mt-8 rounded-lg bg-primary px-6 py-2.5 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
          >
            View pricing plans
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-bg-base px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white">Create account</h1>
          <p className="mt-2 text-sm text-gray-400">Start finding arbitrage opportunities</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-gray-400">Email</span>
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-lg border border-border bg-bg-surface px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:border-primary focus:outline-none"
              placeholder="you@example.com"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-gray-400">Password</span>
            <input
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-lg border border-border bg-bg-surface px-3 py-2.5 text-sm text-white placeholder-gray-600 focus:border-primary focus:outline-none"
              placeholder="Min. 8 characters"
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
            className="mt-1 rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {isPending ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link to="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}