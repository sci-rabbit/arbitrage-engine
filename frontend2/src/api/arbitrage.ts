import { aggApi } from './client'
import type { ArbitragePairRaw } from '../types'

export interface ArbitrageStats {
  count: number
  best_spread: number
  platforms: number
}

export const arbitrageApi = {
  scanCache: () =>
    aggApi.get<ArbitragePairRaw[]>('/arbitrage/scan_cache'),

  stats: () =>
    aggApi.get<ArbitrageStats>('/arbitrage/stats'),
}