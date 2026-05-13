import { useState, useCallback, useRef } from 'react'

const STORAGE_KEY = 'arb_sound_enabled'

function beep(ctx: AudioContext, freq: number, duration: number, startTime: number, gain = 0.25) {
  const osc = ctx.createOscillator()
  const g = ctx.createGain()
  osc.connect(g)
  g.connect(ctx.destination)
  osc.type = 'sine'
  osc.frequency.value = freq
  g.gain.setValueAtTime(0, startTime)
  g.gain.linearRampToValueAtTime(gain, startTime + 0.01)
  g.gain.linearRampToValueAtTime(0, startTime + duration)
  osc.start(startTime)
  osc.stop(startTime + duration + 0.05)
}

export function useSound() {
  const [enabled, setEnabled] = useState<boolean>(() => {
    try { return localStorage.getItem(STORAGE_KEY) !== 'false' } catch { return true }
  })

  const ctxRef = useRef<AudioContext | null>(null)

  const ctx = useCallback(() => {
    if (!ctxRef.current) ctxRef.current = new AudioContext()
    return ctxRef.current
  }, [])

  const toggle = useCallback(() => {
    setEnabled((prev) => {
      const next = !prev
      try { localStorage.setItem(STORAGE_KEY, String(next)) } catch {}
      return next
    })
  }, [])

  const playNewPair = useCallback(() => {
    if (!enabled) return
    try {
      const c = ctx()
      const t = c.currentTime
      beep(c, 880, 0.14, t)
      beep(c, 1100, 0.14, t + 0.17)
    } catch {}
  }, [enabled, ctx])

  const playSpreadChange = useCallback(() => {
    if (!enabled) return
    try {
      const c = ctx()
      beep(c, 660, 0.12, c.currentTime, 0.18)
    } catch {}
  }, [enabled, ctx])

  return { enabled, toggle, playNewPair, playSpreadChange }
}