export interface MarketInfo {
  id: number
  platform: string
  platform_market_id: string
  title: string
  close_time: string | null
  url?: string | null
}

export interface ArbitrageOpportunity {
  direction: string
  entry_price_1: number
  entry_price_2: number
  min_spread: number
  max_spread: number
  min_size_per_market: number
  final_contracts: number
  pnl_at_min_spread: number
  pnl_at_max_spread: number
}

export interface ArbitragePairRaw {
  market_a: MarketInfo
  market_b: MarketInfo
  distance: number
  final_score: number
  arbitrage: ArbitrageOpportunity[]
}

export interface ArbitrageRow {
  id: string
  marketA: MarketInfo
  marketB: MarketInfo
  direction: string
  entryPrice1: number
  entryPrice2: number
  minSpread: number
  maxSpread: number
  sizeMinSpread: number
  sizeMaxSpread: number
  pnlMinSpread: number
  pnlMaxSpread: number
  apy: number
  closeTime: string | null
  distance: number
  finalScore: number
}

export interface ArbitrageFilters {
  priceThreshold: number
  minSize: number
  thresholdDistance: number
  thresholdFinalScore: number
  minSpread: number
  minApy: number
}

export interface TokenPayload {
  sub: string
  type: 'access' | 'refresh' | 'verify' | 'reset'
  has_access: boolean
  exp: number
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
}

export type Plan = 'weekly' | 'monthly' | 'yearly'

export interface PlanConfig {
  id: Plan
  label: string
  price: number
  duration: string
  savingsLabel?: string
  popular?: boolean
}

export interface CryptoPayment {
  id: number
  nowpayments_id: string
  pay_address: string
  pay_currency: string
  pay_amount: string
  price_amount: string
  payment_status: string
}

export interface Notification {
  id: string
  type: 'new_pair' | 'spread_change'
  pair: string
  spreadType?: 'min' | 'max'
  oldSpread?: number
  newSpread?: number
  minSpread: number
  maxSpread: number
  timestamp: number
}