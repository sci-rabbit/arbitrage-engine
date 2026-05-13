import type { ArbitrageRow } from '../../types'
import { fmtPct } from '../../utils/formatters'
import { platformLabel } from '../../utils/formatters'

interface Props {
  rows: ArbitrageRow[]
}

export function Ticker({ rows }: Props) {
  if (!rows.length) return null

  const items = [...rows, ...rows]

  return (
    <div className="overflow-hidden border-b border-border bg-bg-surface py-2 text-xs">
      <div className="flex animate-ticker gap-12 whitespace-nowrap">
        {items.map((row, i) => (
          <span key={`${row.id}_${i}`} className="flex items-center gap-2 text-gray-400">
            <span className="h-1.5 w-1.5 rounded-full bg-success" />
            <span className="text-white font-medium">
              {platformLabel(row.marketA.platform)} / {platformLabel(row.marketB.platform)}
            </span>
            <span className="font-mono text-success">+{fmtPct(row.minSpread)}</span>
            <span className="text-gray-600">APY {row.apy.toFixed(0)}%</span>
          </span>
        ))}
      </div>
    </div>
  )
}