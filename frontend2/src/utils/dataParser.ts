import type { ArbitragePairRaw, ArbitrageRow } from '../types'
import { calculateAPY } from './calculations'

export function parseArbitrageData(raw: ArbitragePairRaw[]): ArbitrageRow[] {
  const rows: ArbitrageRow[] = []

  for (const pair of raw) {
    for (const arb of pair.arbitrage) {
      const closeTime =
        pair.market_a.close_time && pair.market_b.close_time
          ? new Date(pair.market_a.close_time) < new Date(pair.market_b.close_time)
            ? pair.market_a.close_time
            : pair.market_b.close_time
          : pair.market_a.close_time ?? pair.market_b.close_time

      rows.push({
        id: `${pair.market_a.platform_market_id}_${pair.market_b.platform_market_id}_${arb.direction}`,
        marketA: pair.market_a,
        marketB: pair.market_b,
        direction: arb.direction,
        entryPrice1: arb.entry_price_1,
        entryPrice2: arb.entry_price_2,
        minSpread: arb.min_spread,
        maxSpread: arb.max_spread,
        sizeMinSpread: arb.final_contracts,
        sizeMaxSpread: arb.min_size_per_market,
        pnlMinSpread: arb.pnl_at_min_spread,
        pnlMaxSpread: arb.pnl_at_max_spread,
        apy: calculateAPY(arb.min_spread, closeTime),
        closeTime,
        distance: pair.distance,
        finalScore: pair.final_score,
      })
    }
  }

  return rows
}