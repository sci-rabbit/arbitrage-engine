import { useState } from 'react'
import { useParams, Navigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { QRCodeSVG } from 'qrcode.react'
import { paymentsApi } from '../api/payments'
import type { CryptoPayment, Plan } from '../types'

const PLAN_DETAILS: Record<Plan, { label: string; price: number; duration: string }> = {
  weekly: { label: 'Weekly', price: 9.99, duration: '7 days' },
  monthly: { label: 'Monthly', price: 29.99, duration: '30 days' },
  yearly: { label: 'Yearly', price: 199.99, duration: '365 days' },
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={copy}
      className="ml-2 rounded px-2 py-0.5 text-xs text-gray-400 border border-border hover:text-white hover:border-gray-500 transition-colors"
    >
      {copied ? 'Copied!' : 'Copy'}
    </button>
  )
}

function PaymentDetails({ payment }: { payment: CryptoPayment }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex justify-center">
        <div className="rounded-xl border border-border bg-white p-4">
          <QRCodeSVG value={payment.pay_address} size={180} />
        </div>
      </div>

      <div className="flex flex-col gap-3 rounded-xl border border-border bg-bg-surface p-4 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-gray-500">Amount</span>
          <span className="font-mono font-semibold text-white">
            {payment.pay_amount} {payment.pay_currency.toUpperCase()}
          </span>
        </div>
        <div>
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Address</span>
            <CopyButton text={payment.pay_address} />
          </div>
          <p className="mt-1 break-all font-mono text-xs text-white">{payment.pay_address}</p>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500">Status</span>
          <span className="capitalize text-warning">{payment.payment_status}</span>
        </div>
      </div>

      <p className="text-center text-xs text-gray-500">
        Send exactly the amount above to the address. Access is activated automatically after
        network confirmation.
      </p>
    </div>
  )
}

export function Payment() {
  const { planId } = useParams<{ planId: string }>()
  const plan = PLAN_DETAILS[planId as Plan]
  const [currency, setCurrency] = useState('')
  const [payment, setPayment] = useState<CryptoPayment | null>(null)

  const { data: currenciesData, isLoading: loadingCurrencies } = useQuery({
    queryKey: ['currencies'],
    queryFn: () => paymentsApi.getCurrencies().then((r) => r.data),
  })

  const { mutate: createPayment, isPending, error } = useMutation({
    mutationFn: () => paymentsApi.createPayment(plan.price, currency),
    onSuccess: ({ data }) => setPayment(data),
  })

  if (!plan) return <Navigate to="/pricing" replace />

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-bg-base px-4 py-12">
      <div className="w-full max-w-md">
        {/* Plan summary */}
        <div className="mb-6 rounded-xl border border-border bg-bg-card p-4 text-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-semibold text-white">{plan.label} plan</p>
              <p className="text-gray-500">{plan.duration} access</p>
            </div>
            <p className="text-xl font-bold text-white">${plan.price}</p>
          </div>
        </div>

        {payment ? (
          <PaymentDetails payment={payment} />
        ) : (
          <div className="flex flex-col gap-4">
            <h2 className="text-lg font-semibold text-white">Select currency</h2>

            {loadingCurrencies ? (
              <div className="h-10 animate-pulse rounded-lg border border-border bg-bg-surface" />
            ) : (
              <select
                value={currency}
                onChange={(e) => setCurrency(e.target.value)}
                className="rounded-lg border border-border bg-bg-surface px-3 py-2.5 text-sm text-white focus:border-primary focus:outline-none"
              >
                <option value="">Choose crypto…</option>
                {currenciesData?.map((c) => (
                  <option key={c} value={c}>
                    {c.toUpperCase()}
                  </option>
                ))}
              </select>
            )}

            {error && (
              <p className="rounded-lg border border-danger/20 bg-danger/5 px-3 py-2 text-sm text-danger">
                Failed to create payment. Please try again.
              </p>
            )}

            <button
              onClick={() => createPayment()}
              disabled={!currency || isPending}
              className="rounded-lg bg-primary py-2.5 text-sm font-semibold text-white hover:bg-primary-hover disabled:opacity-50 transition-colors"
            >
              {isPending ? 'Generating address…' : 'Generate payment address'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}