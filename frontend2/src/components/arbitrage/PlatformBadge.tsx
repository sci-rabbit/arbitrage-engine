import clsx from 'clsx'
import { platformLabel } from '../../utils/formatters'

const platformClasses: Record<string, string> = {
  polymarket: 'bg-polymarket/10 text-polymarket border-polymarket/20',
  kalshi: 'bg-kalshi/10 text-kalshi border-kalshi/20',
  predict_fun: 'bg-predict/10 text-predict border-predict/20',
}

interface Props {
  platform: string
  url?: string | null
}

export function PlatformBadge({ platform, url }: Props) {
  const key = platform.toLowerCase()
  const className = clsx(
    'inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide',
    platformClasses[key] ?? 'bg-gray-800 text-gray-400 border-gray-700',
    url && 'hover:opacity-80 cursor-pointer',
  )

  if (url) {
    return (
      <a href={url} target="_blank" rel="noopener noreferrer" className={className}>
        {platformLabel(platform)}
      </a>
    )
  }

  return <span className={className}>{platformLabel(platform)}</span>
}