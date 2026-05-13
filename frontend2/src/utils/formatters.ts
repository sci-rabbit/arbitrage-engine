export const fmtPct = (v: number) => `${(v * 100).toFixed(2)}%`
export const fmtApy = (v: number) => `${v.toFixed(1)}%`
export const fmtPrice = (v: number) => `$${v.toFixed(2)}`
export const fmtCents = (v: number) => {
  const cents = v * 100
  if (cents === 0) return '0¢'
  if (cents < 1) return `${cents.toFixed(1)}¢`
  return `${Math.round(cents)}¢`
}
export const fmtPnl = (v: number) => `$${v.toFixed(2)}`

export function fmtCloseTime(closeTime: string | null): string {
  if (!closeTime) return '—'
  const d = new Date(closeTime)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function timeAgo(timestamp: number): string {
  const secs = Math.floor((Date.now() - timestamp) / 1000)
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m`
}

export function platformLabel(platform: string): string {
  const map: Record<string, string> = {
    polymarket: 'Polymarket',
    kalshi: 'Kalshi',
    predict_fun: 'Predict.fun',
  }
  return map[platform.toLowerCase()] ?? platform
}