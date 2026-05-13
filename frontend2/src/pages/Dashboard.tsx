import { useState } from 'react'
import type { ArbitrageFilters } from '../types'
import { useArbitrage } from '../hooks/useArbitrage'
import { useSound } from '../hooks/useSound'
import { Ticker } from '../components/arbitrage/Ticker'
import { Filters } from '../components/arbitrage/Filters'
import { ArbitrageGrid } from '../components/arbitrage/ArbitrageGrid'
import { NotificationFeed } from '../components/arbitrage/NotificationFeed'

const DEFAULT_FILTERS: ArbitrageFilters = {
  priceThreshold: 0.97,
  minSize: 25,
  thresholdDistance: 0.7,
  thresholdFinalScore: 0.7,
  minSpread: 0,
  minApy: 0,
}

export function Dashboard() {
  const [filters, setFilters] = useState<ArbitrageFilters>(DEFAULT_FILTERS)
  const { enabled: soundEnabled, toggle: toggleSound, playNewPair, playSpreadChange } = useSound()
  const { rows, allRows, isLoading, error, notifications, setNotifications } = useArbitrage(
    filters,
    (type) => (type === 'new_pair' ? playNewPair() : playSpreadChange()),
  )

  return (
    <div className="min-h-[calc(100vh-56px)] bg-bg-base">
      {allRows.length > 0 && <Ticker rows={allRows} />}

      <div className="mx-auto max-w-7xl px-4 py-6">
        {/* Title row */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white">Arbitrage Scanner</h1>
            <p className="mt-0.5 text-sm text-gray-500">
              {rows.length} opportunit{rows.length === 1 ? 'y' : 'ies'} · live
              <span className="ml-2 inline-block h-1.5 w-1.5 rounded-full bg-success align-middle" />
            </p>
          </div>
          <NotificationFeed
            notifications={notifications}
            onClear={() => setNotifications([])}
            soundEnabled={soundEnabled}
            onToggleSound={toggleSound}
          />
        </div>

        {/* Filters */}
        <div className="mb-6">
          <Filters filters={filters} onChange={setFilters} />
        </div>

        {/* Grid */}
        <ArbitrageGrid
          rows={rows}
          isLoading={isLoading}
          error={error as Error | null}
        />
      </div>
    </div>
  )
}