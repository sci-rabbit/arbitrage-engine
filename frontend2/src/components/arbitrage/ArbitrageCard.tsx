import clsx from 'clsx'
import type { ArbitrageRow } from '../../types'
import { PlatformBadge } from './PlatformBadge'
import { fmtPct, fmtApy, fmtCents, fmtPnl, fmtCloseTime } from '../../utils/formatters'

interface Props {
  row: ArbitrageRow
}

export function ArbitrageCard({ row }: Props) {
  const spreadClass = row.minSpread > 0 ? 'text-success' : 'text-danger'
  const [side1, side2] = row.direction.split(' + ')

  return (
    <div className="flex flex-col rounded-xl border border-border bg-bg-card hover:border-gray-600 transition-colors animate-slide-up">
      {/* Header */}
      <div className="flex items-start justify-between p-4 pb-3">
        <div className="flex flex-wrap gap-1.5">
          <PlatformBadge platform={row.marketA.platform} url={row.marketA.url} />
          <PlatformBadge platform={row.marketB.platform} url={row.marketB.url} />
        </div>
        <div className="text-right">
          <div className={clsx('font-mono text-lg font-semibold', spreadClass)}>
            +{fmtPct(row.minSpread)}
            {row.maxSpread > row.minSpread && (
              <span className="text-sm font-normal text-gray-500 ml-1">
                – +{fmtPct(row.maxSpread)}
              </span>
            )}
          </div>
          <div className="text-[11px] text-gray-500">APY {fmtApy(row.apy)}</div>
        </div>
      </div>

      {/* Markets */}
      <div className="px-4 pb-3">
        {row.marketA.url ? (
          <a href={row.marketA.url} target="_blank" rel="noopener noreferrer"
            className="text-sm text-white font-medium leading-snug line-clamp-2 hover:underline">
            {row.marketA.title}
          </a>
        ) : (
          <p className="text-sm text-white font-medium leading-snug line-clamp-2">{row.marketA.title}</p>
        )}
        <p className="mt-0.5 text-xs text-gray-500">vs</p>
        {row.marketB.url ? (
          <a href={row.marketB.url} target="_blank" rel="noopener noreferrer"
            className="text-sm text-white font-medium leading-snug line-clamp-2 hover:underline">
            {row.marketB.title}
          </a>
        ) : (
          <p className="text-sm text-white font-medium leading-snug line-clamp-2">{row.marketB.title}</p>
        )}
        {row.closeTime && (
          <p className="mt-2 text-[11px] text-gray-600">
            Closes {fmtCloseTime(row.closeTime)}
          </p>
        )}
      </div>

      {/* Divider */}
      <div className="mx-4 border-t border-border" />

      {/* Entries */}
      <div className="grid grid-cols-2 gap-px bg-border rounded-b-xl overflow-hidden">
        {/* Side 1 */}
        <div className="bg-bg-card p-3">
          <div className="text-[11px] text-gray-500 uppercase tracking-wide mb-1.5">
            {side1} · {row.marketA.platform}
          </div>
          <div className="font-mono text-white text-sm font-semibold">{fmtCents(row.entryPrice1)}</div>
          <div className="text-[11px] text-gray-500 mt-0.5">Size: {Math.round(row.sizeMinSpread)}</div>
          <div className={clsx('text-[11px] mt-0.5 font-mono', spreadClass)}>
            min {fmtPnl(row.pnlMinSpread)}
          </div>
          <div className={clsx('text-[11px] mt-0.5 font-mono', spreadClass)}>
            max {fmtPnl(row.pnlMaxSpread)}
          </div>
        </div>

        {/* Side 2 */}
        <div className="bg-bg-card p-3">
          <div className="text-[11px] text-gray-500 uppercase tracking-wide mb-1.5">
            {side2} · {row.marketB.platform}
          </div>
          <div className="font-mono text-white text-sm font-semibold">{fmtCents(row.entryPrice2)}</div>
          <div className="text-[11px] text-gray-500 mt-0.5">Size: {Math.round(row.sizeMaxSpread)}</div>
          <div className={clsx('text-[11px] mt-0.5 font-mono', spreadClass)}>
            min +{fmtPct(row.minSpread)}
          </div>
          <div className={clsx('text-[11px] mt-0.5 font-mono', spreadClass)}>
            max +{fmtPct(row.maxSpread)}
          </div>
        </div>
      </div>
    </div>
  )
}