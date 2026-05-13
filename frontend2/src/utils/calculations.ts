export function calculateAPY(spread: number, closeTime: string | null): number {
  let days = 30
  if (closeTime) {
    const ms = new Date(closeTime).getTime() - Date.now()
    days = Math.max(ms / (1000 * 60 * 60 * 24), 1)
  }
  if (spread <= 0 || spread >= 1) return 0
  return (spread / (1 - spread)) * (365 / days) * 100
}