import type { PlanConfig } from '../types'
import { PricingCard } from '../components/pricing/PricingCard'

const PLANS: PlanConfig[] = [
  {
    id: 'weekly',
    label: 'Weekly',
    price: 9.99,
    duration: 'week',
  },
  {
    id: 'monthly',
    label: 'Monthly',
    price: 29.99,
    duration: 'month',
    savingsLabel: 'Save 25% vs weekly',
    popular: true,
  },
  {
    id: 'yearly',
    label: 'Yearly',
    price: 199.99,
    duration: 'year',
    savingsLabel: 'Save 58% vs monthly',
  },
]

export function Pricing() {
  return (
    <div className="min-h-[calc(100vh-56px)] bg-bg-base px-4 py-16">
      <div className="mx-auto max-w-4xl">
        <div className="mb-12 text-center">
          <h1 className="text-3xl font-bold text-white">Simple pricing</h1>
          <p className="mt-3 text-gray-400">
            All plans include full access. Pay with crypto via NOWPayments.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
          {PLANS.map((plan) => (
            <PricingCard key={plan.id} plan={plan} />
          ))}
        </div>

        <p className="mt-10 text-center text-xs text-gray-600">
          Payments processed securely via NOWPayments. Access activated automatically after
          confirmation.
        </p>
      </div>
    </div>
  )
}