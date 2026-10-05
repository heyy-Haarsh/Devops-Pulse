import { ListTree } from 'lucide-react'
import type { SystemEvent } from '../api'

const dot: Record<string, string> = {
  success: 'bg-emerald-400',
  info: 'bg-cyan-400',
  warning: 'bg-amber-400',
  error: 'bg-rose-500',
}

function timeAgo(ts: string) {
  const diff = (Date.now() - new Date(ts).getTime()) / 1000
  if (Number.isNaN(diff)) return ''
  if (diff < 60) return `${Math.max(0, Math.round(diff))}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export function EventsFeed({ events }: { events: SystemEvent[] }) {
  return (
    <section id="events" className="card">
      <h2 className="card-title">
        <ListTree size={16} /> Recent Events
      </h2>
      <ul className="max-h-96 space-y-3 overflow-y-auto pr-1">
        {events.map((e, i) => (
          <li key={`${e.timestamp}-${i}`} className="flex gap-3">
            <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${dot[e.severity] ?? 'bg-slate-500'}`} />
            <div className="min-w-0 flex-1">
              <div className="text-sm text-slate-200">
                {e.reason && <span className="mr-1.5 font-semibold text-slate-100">{e.reason}</span>}
                {e.message}
              </div>
              <div className="mt-0.5 flex gap-2 text-[11px] text-slate-500">
                <span className="uppercase">{e.type}</span>
                {e.object && <span className="font-mono">{e.object}</span>}
                <span>{timeAgo(e.timestamp)}</span>
              </div>
            </div>
          </li>
        ))}
        {events.length === 0 && <li className="text-sm text-slate-500">No events yet</li>}
      </ul>
    </section>
  )
}
