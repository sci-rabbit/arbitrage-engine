import { useState } from 'react'
import clsx from 'clsx'
import type { Notification } from '../../types'
import { fmtPct, timeAgo } from '../../utils/formatters'

interface Props {
  notifications: Notification[]
  onClear: () => void
  soundEnabled: boolean
  onToggleSound: () => void
}

export function NotificationFeed({ notifications, onClear, soundEnabled, onToggleSound }: Props) {
  const [open, setOpen] = useState(false)
  const [readAt, setReadAt] = useState(0)
  const unread = notifications.filter((n) => n.timestamp > readAt).length

  return (
    <div className="relative">
      <button
        onClick={() => { setOpen((o) => { if (!o) setReadAt(Date.now()); return !o }) }}
        className="relative flex h-8 w-8 items-center justify-center rounded-lg border border-border bg-bg-elevated text-gray-400 hover:text-white transition-colors"
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-[10px] font-medium text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 rounded-xl border border-border bg-bg-elevated shadow-2xl animate-fade-in">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <span className="text-sm font-medium text-white">Notifications</span>
            <div className="flex items-center gap-3">
              <button
                onClick={onToggleSound}
                title={soundEnabled ? 'Mute sounds' : 'Enable sounds'}
                className="text-gray-500 hover:text-white transition-colors"
              >
                {soundEnabled ? (
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072M12 6v12m0 0l-3-3m3 3l3-3M9 9H5a1 1 0 00-1 1v4a1 1 0 001 1h4l5 5V4L9 9z" />
                  </svg>
                ) : (
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2" />
                  </svg>
                )}
              </button>
              <button
                onClick={() => { onClear(); setOpen(false) }}
                className="text-xs text-gray-500 hover:text-white transition-colors"
              >
                Clear all
              </button>
            </div>
          </div>

          <div className="max-h-72 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="p-4 text-center text-sm text-gray-500">No notifications</p>
            ) : (
              notifications.map((n) => (
                <div key={n.id} className="flex items-start gap-3 px-4 py-3 border-b border-border/50 last:border-0">
                  <span
                    className={clsx(
                      'mt-1 h-2 w-2 flex-shrink-0 rounded-full',
                      n.type === 'new_pair' ? 'bg-primary' : 'bg-warning',
                    )}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-white font-medium truncate">{n.pair}</p>
                    {n.type === 'new_pair' ? (
                      <p className="text-[11px] text-gray-400 mt-0.5">
                        New opportunity · spread {fmtPct(n.minSpread)}
                      </p>
                    ) : (
                      <p className="text-[11px] text-gray-400 mt-0.5">
                        {n.spreadType === 'min' ? 'Min' : 'Max'} spread{' '}
                        {fmtPct(n.oldSpread ?? 0)} → {fmtPct(n.newSpread ?? 0)}
                      </p>
                    )}
                  </div>
                  <span className="text-[11px] text-gray-600 flex-shrink-0">
                    {timeAgo(n.timestamp)}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  )
}