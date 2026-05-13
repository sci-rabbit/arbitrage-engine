import type { ArbitrageRow } from '../../types'
import { ArbitrageCard } from './ArbitrageCard'

interface Props {
  rows: ArbitrageRow[]
  isLoading: boolean
  error: Error | null
}

export function ArbitrageGrid({ rows, isLoading, error }: Props) {
  if (isLoading && !rows.length) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-56 rounded-xl border border-border bg-bg-card animate-pulse" />
        ))}
      </div>
    )
  }

  if (error && !rows.length) {
    return (
      <div className="rounded-xl border border-danger/20 bg-danger/5 p-6 text-center text-sm text-danger">
        Unable to load data. Please try again later.
      </div>
    )
  }

  if (!rows.length) {
    return (
      <div className="rounded-xl border border-border bg-bg-card p-12 text-center text-gray-500">
        No arbitrage opportunities match your filters.
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {rows.map((row) => (
        <ArbitrageCard key={row.id} row={row} />
      ))}
    </div>
  )
}