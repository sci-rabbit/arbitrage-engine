import type { ArbitrageFilters } from '../../types'

interface Props {
  filters: ArbitrageFilters
  onChange: (f: ArbitrageFilters) => void
}

function Field({
  label,
  value,
  onChange,
  step = 0.01,
}: {
  label: string
  value: number
  onChange: (v: number) => void
  step?: number
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[11px] text-gray-500 uppercase tracking-wide">{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
        className="w-24 rounded border border-border bg-bg-elevated px-2 py-1.5 text-sm text-white focus:border-primary focus:outline-none"
      />
    </label>
  )
}

export function Filters({ filters, onChange }: Props) {
  const set = (patch: Partial<ArbitrageFilters>) => onChange({ ...filters, ...patch })

  return (
    <div className="flex flex-wrap items-end gap-4 rounded-lg border border-border bg-bg-surface p-4">
      <Field
        label="Price threshold"
        value={filters.priceThreshold}
        onChange={(v) => set({ priceThreshold: v })}
      />
      <Field
        label="Min size"
        value={filters.minSize}
        onChange={(v) => set({ minSize: v })}
        step={1}
      />
      <Field
        label="Distance"
        value={filters.thresholdDistance}
        onChange={(v) => set({ thresholdDistance: v })}
      />
      <Field
        label="Score"
        value={filters.thresholdFinalScore}
        onChange={(v) => set({ thresholdFinalScore: v })}
      />
      <div className="h-px w-full sm:h-auto sm:w-px bg-border self-stretch" />
      <Field
        label="Min spread %"
        value={filters.minSpread}
        onChange={(v) => set({ minSpread: v })}
      />
      <Field
        label="Min APY %"
        value={filters.minApy}
        onChange={(v) => set({ minApy: v })}
        step={1}
      />
    </div>
  )
}