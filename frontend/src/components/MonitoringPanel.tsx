import { BellRing, ExternalLink, Flame, Target } from 'lucide-react'
import type { MonitoringInfo } from '../api'

export function MonitoringPanel({ monitoring }: { monitoring?: MonitoringInfo }) {
  const prom = monitoring?.prometheus
  const graf = monitoring?.grafana
  const alerts = prom?.alerts ?? []

  return (
    <div className="card">
      <h2 className="card-title">
        <Flame size={16} /> Monitoring Stack
      </h2>

      <div className="mb-4 grid grid-cols-2 gap-3">
        <a
          href={prom?.url}
          target="_blank"
          rel="noreferrer"
          className="group rounded-lg border border-slate-800 bg-slate-950/50 p-3 transition hover:border-orange-500/50"
        >
          <div className="flex items-center justify-between text-xs text-slate-500">
            Prometheus <ExternalLink size={12} className="opacity-0 transition group-hover:opacity-100" />
          </div>
          <div className="mt-1 text-sm font-semibold capitalize text-white">{prom?.status?.replace('_', ' ') ?? '…'}</div>
          <div className="text-xs text-slate-400">
            {prom?.targets_total !== undefined ? `${prom.targets_up}/${prom.targets_total} targets UP` : 'no data'}
          </div>
        </a>
        <a
          href={graf?.url}
          target="_blank"
          rel="noreferrer"
          className="group rounded-lg border border-slate-800 bg-slate-950/50 p-3 transition hover:border-amber-500/50"
        >
          <div className="flex items-center justify-between text-xs text-slate-500">
            Grafana <ExternalLink size={12} className="opacity-0 transition group-hover:opacity-100" />
          </div>
          <div className="mt-1 text-sm font-semibold capitalize text-white">{graf?.status?.replace('_', ' ') ?? '…'}</div>
          <div className="text-xs text-slate-400">
            {graf?.version ? `v${graf.version} · ${graf.dashboards ?? 0} dashboard(s)` : 'no data'}
          </div>
        </a>
      </div>

      <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
        <Target size={13} /> Scrape targets
      </div>
      <ul className="mb-4 space-y-1.5">
        {(prom?.targets ?? []).map((t) => (
          <li key={t.instance} className="flex items-center justify-between rounded bg-slate-950/50 px-3 py-1.5 text-xs">
            <span className="truncate font-mono text-slate-300" title={t.last_error || t.instance}>
              {t.pod ?? t.instance}
            </span>
            <span
              className={`rounded px-1.5 py-0.5 font-semibold uppercase ${
                t.health === 'up' ? 'bg-emerald-500/15 text-emerald-300' : 'bg-rose-500/15 text-rose-300'
              }`}
            >
              {t.health}
            </span>
          </li>
        ))}
        {(prom?.targets ?? []).length === 0 && <li className="text-xs text-slate-500">No targets discovered</li>}
      </ul>

      <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-slate-500">
        <BellRing size={13} /> Alerts
      </div>
      <ul className="space-y-1.5">
        {alerts.map((a) => (
          <li
            key={a.name}
            className={`rounded px-3 py-1.5 text-xs ${
              a.state === 'firing' ? 'bg-rose-500/15 text-rose-200' : 'bg-amber-500/10 text-amber-200'
            }`}
          >
            <span className="font-semibold">{a.name}</span> · {a.state} — {a.summary}
          </li>
        ))}
        {alerts.length === 0 && <li className="text-xs text-emerald-400/80">No active alerts</li>}
      </ul>
    </div>
  )
}
