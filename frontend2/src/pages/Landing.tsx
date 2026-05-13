import { Link } from 'react-router-dom'
import { Ticker } from '../components/arbitrage/Ticker'
import { useAuthStore } from '../store/auth'
import { useQuery } from '@tanstack/react-query'
import { arbitrageApi } from '../api/arbitrage'
import { parseArbitrageData } from '../utils/dataParser'

const DEMO_PLATFORMS = ['Polymarket', 'Kalshi', 'Predict.fun']

export function Landing() {
  const { isAuthenticated, hasAccess } = useAuthStore()

  const { data: raw } = useQuery({
    queryKey: ['arbitrage-ticker'],
    queryFn: () => arbitrageApi.scanCache().then((r) => r.data),
    refetchInterval: 5000,
    retry: false,
  })

  const { data: stats } = useQuery({
    queryKey: ['arbitrage-stats'],
    queryFn: () => arbitrageApi.stats().then((r) => r.data),
    refetchInterval: 30000,
    retry: false,
  })

  const rows = raw ? parseArbitrageData(raw) : []

  return (
    <div className="min-h-screen bg-bg-base">
      {rows.length > 0 && <Ticker rows={rows} />}

      {/* Hero */}
      <section className="mx-auto max-w-5xl px-4 py-24 text-center">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-bg-surface px-3 py-1 text-xs text-gray-400">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
          Live data · {DEMO_PLATFORMS.join(' · ')}
        </div>

        <h1 className="text-5xl font-bold tracking-tight text-white sm:text-6xl">
          You don&apos;t need
          <br />
          <span className="text-primary">to gamble.</span>
        </h1>

        <p className="mx-auto mt-6 max-w-xl text-lg text-gray-400">
          Arbitrage with Prediction Markets. Find price discrepancies across Polymarket, Kalshi, and
          Predict.fun in real time.
        </p>

        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          {isAuthenticated && hasAccess ? (
            <Link
              to="/dashboard"
              className="rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
            >
              Open Scanner
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="rounded-lg bg-primary px-6 py-3 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
              >
                Arbitrage Opportunities →
              </Link>
              <Link
                to="/pricing"
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                View pricing
              </Link>
            </>
          )}
        </div>
      </section>

      {/* Stats — visible to all users, powered by public /arbitrage/stats */}
      {stats && stats.count > 0 && (
        <section className="border-y border-border bg-bg-surface py-10">
          <div className="mx-auto grid max-w-4xl grid-cols-3 gap-8 px-4 text-center">
            <div>
              <div className="text-3xl font-bold text-white">{stats.count}</div>
              <div className="mt-1 text-sm text-gray-500">Live opportunities</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-success">
                +{(stats.best_spread * 100).toFixed(1)}%
              </div>
              <div className="mt-1 text-sm text-gray-500">Best spread</div>
            </div>
            <div>
              <div className="text-3xl font-bold text-white">{stats.platforms}</div>
              <div className="mt-1 text-sm text-gray-500">Platforms</div>
            </div>
          </div>
        </section>
      )}

      {/* How it works */}
      <section className="mx-auto max-w-5xl px-4 py-20">
        <h2 className="text-center text-2xl font-bold text-white">How it works</h2>
        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-3">
          {[
            {
              icon: '⬡',
              title: 'We scan markets',
              body: 'Our engine continuously monitors all open markets across Polymarket, Kalshi, and Predict.fun.',
            },
            {
              icon: '⇄',
              title: 'We find mismatches',
              body: 'Semantic matching identifies the same event priced differently across platforms.',
            },
            {
              icon: '↑',
              title: 'You earn the spread',
              body: 'Buy the underpriced YES and the underpriced NO. Collect when markets settle.',
            },
          ].map((s) => (
            <div key={s.title} className="rounded-xl border border-border bg-bg-card p-6">
              <div className="mb-4 text-2xl text-primary">{s.icon}</div>
              <h3 className="font-semibold text-white">{s.title}</h3>
              <p className="mt-2 text-sm text-gray-400">{s.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Platforms */}
      <section className="border-t border-border bg-bg-surface py-12">
        <div className="mx-auto max-w-4xl px-4 text-center">
          <p className="text-sm text-gray-500 mb-8">Markets covered</p>
          <div className="flex justify-center gap-8">
            {DEMO_PLATFORMS.map((p) => (
              <span key={p} className="text-lg font-semibold text-gray-400 hover:text-white transition-colors">
                {p}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-2xl px-4 py-24 text-center">
        <h2 className="text-3xl font-bold text-white">Ready to start?</h2>
        <p className="mt-4 text-gray-400">
          Join traders who use Arbitrage Engine to find and capture prediction market inefficiencies.
        </p>
        <Link
          to="/register"
          className="mt-8 inline-block rounded-lg bg-primary px-8 py-3 text-sm font-semibold text-white hover:bg-primary-hover transition-colors"
        >
          Create free account
        </Link>
      </section>
    </div>
  )
}