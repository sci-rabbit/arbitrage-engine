import { useQuery } from '@tanstack/react-query'
import { useMemo, useRef, useEffect, useState } from 'react'
import { arbitrageApi } from '../api/arbitrage'
import { parseArbitrageData } from '../utils/dataParser'
import { useAuthStore } from '../store/auth'
import type { ArbitrageRow, ArbitrageFilters, Notification } from '../types'

const NOTIFICATION_TTL = 5 * 60 * 1000

function notify(
  prev: Map<string, ArbitrageRow>,
  next: ArbitrageRow[],
  add: (n: Notification) => void,
) {
  for (const row of next) {
    const old = prev.get(row.id)
    if (!old) {
      add({
        id: `${row.id}_new_${Date.now()}`,
        type: 'new_pair',
        pair: `${row.marketA.title} / ${row.marketB.title}`,
        minSpread: row.minSpread,
        maxSpread: row.maxSpread,
        timestamp: Date.now(),
      })
      continue
    }
    const delta = 0.0001
    if (Math.abs(old.minSpread - row.minSpread) > delta) {
      add({
        id: `${row.id}_min_${Date.now()}`,
        type: 'spread_change',
        pair: `${row.marketA.title} / ${row.marketB.title}`,
        spreadType: 'min',
        oldSpread: old.minSpread,
        newSpread: row.minSpread,
        minSpread: row.minSpread,
        maxSpread: row.maxSpread,
        timestamp: Date.now(),
      })
    }
    if (Math.abs(old.maxSpread - row.maxSpread) > delta) {
      add({
        id: `${row.id}_max_${Date.now()}`,
        type: 'spread_change',
        pair: `${row.marketA.title} / ${row.marketB.title}`,
        spreadType: 'max',
        oldSpread: old.maxSpread,
        newSpread: row.maxSpread,
        minSpread: row.minSpread,
        maxSpread: row.maxSpread,
        timestamp: Date.now(),
      })
    }
  }
}

export function useArbitrage(filters: ArbitrageFilters, onNotify?: (type: Notification['type']) => void) {
  const hasAccess = useAuthStore((s) => s.hasAccess)
  const prevRef = useRef<Map<string, ArbitrageRow>>(new Map())
  const [notifications, setNotifications] = useState<Notification[]>([])

  const { data: raw, isLoading, error } = useQuery({
    queryKey: ['arbitrage', filters.priceThreshold, filters.minSize, filters.thresholdDistance, filters.thresholdFinalScore],
    queryFn: () => arbitrageApi.scanCache().then((r) => r.data),
    refetchInterval: 10_000,
    staleTime: 5_000,
    retry: false,
    enabled: hasAccess,
  })

  const allRows = useMemo(() => (raw ? parseArbitrageData(raw) : []), [raw])

  useEffect(() => {
    if (!allRows.length) return
    const prev = prevRef.current
    notify(prev, allRows, (n) => {
      setNotifications((ns) => [n, ...ns].slice(0, 50))
      onNotify?.(n.type)
    })
    prevRef.current = new Map(allRows.map((r) => [r.id, r]))
  }, [allRows])

  useEffect(() => {
    const id = setInterval(
      () => setNotifications((ns) => ns.filter((n) => Date.now() - n.timestamp < NOTIFICATION_TTL)),
      10_000,
    )
    return () => clearInterval(id)
  }, [])

  const rows = useMemo(
    () =>
      allRows
        .filter((r) =>
          r.minSpread >= filters.minSpread &&
          r.apy >= filters.minApy &&
          r.distance <= filters.thresholdDistance &&
          r.finalScore >= filters.thresholdFinalScore
        )
        .sort((a, b) => b.apy - a.apy),
    [allRows, filters.minSpread, filters.minApy, filters.thresholdDistance, filters.thresholdFinalScore],
  )

  return { rows, allRows, isLoading, error, notifications, setNotifications }
}