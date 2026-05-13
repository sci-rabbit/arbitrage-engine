import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import type { PlanConfig } from '../../types'
import { useAuthStore } from '../../store/auth'

const FEATURES = [
  'Real-time arbitrage scanner',
  'Polymarket · Kalshi · Predict.fun',
  'Spread & APY filters',
  'Live notifications',
  'API access for agents',
]

interface Props {
  plan: PlanConfig
}

export function PricingCard({ plan }: Props) {
  const navigate = useNavigate()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const handleClick = () => {
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    navigate(`/payment/${plan.id}`)
  }

  return (
    <div
      className={clsx(
        'relative flex flex-col rounded-2xl border p-6 transition-all',
        plan.popular
          ? 'border-primary bg-bg-elevated shadow-lg shadow-primary/10'
          : 'border-border bg-bg-card hover:border-gray-600',
      )}
    >
      {plan.popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2">
          <span className="rounded-full bg-primary px-3 py-0.5 text-xs font-semibold text-white">
            Most popular
          </span>
        </div>
      )}

      <div className="mb-6">
        <h3 className="text-lg font-semibold text-white">{plan.label}</h3>
        <div className="mt-3 flex items-end gap-1">
          <span className="text-4xl font-bold text-white">${plan.price}</span>
          <span className="mb-1 text-sm text-gray-500">/ {plan.duration}</span>
        </div>
        {plan.savingsLabel && (
          <p className="mt-1 text-xs text-success">{plan.savingsLabel}</p>
        )}
      </div>

      <ul className="mb-8 flex flex-col gap-3">
        {FEATURES.map((f) => (
          <li key={f} className="flex items-center gap-2 text-sm text-gray-300">
            <svg className="h-4 w-4 text-success flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
            </svg>
            {f}
          </li>
        ))}
      </ul>

      <button
        onClick={handleClick}
        className={clsx(
          'mt-auto w-full rounded-lg py-2.5 text-sm font-semibold transition-colors',
          plan.popular
            ? 'bg-primary text-white hover:bg-primary-hover'
            : 'border border-border bg-bg-elevated text-white hover:bg-bg-card',
        )}
      >
        Get started
      </button>
    </div>
  )
}