import { Stethoscope } from 'lucide-react'
import type { Diagnostic } from '../api'
import { StatusIcon, toneClasses } from './StatusDot'

const LABEL = { ok: 'Healthy', warn: 'Degraded', error: 'Failing', off: 'Not configured' }

export function Diagnostics({ checks }: { checks?: Diagnostic[] }) {
  return (
    <div className="card">
      <h2 className="card-title">
        <Stethoscope size={16} /> System Diagnostics
      </h2>
      <ul className="space-y-2.5">
        {(checks ?? []).map((c) => (
          <li key={c.name} className="flex items-center gap-3 rounded-lg bg-slate-950/50 px-3 py-2.5">
            <StatusIcon status={c.status} />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-medium text-slate-200">{c.name}</div>
              <div className="truncate text-xs text-slate-500" title={c.detail}>
                {c.detail}
              </div>
            </div>
            <span className={`text-xs font-semibold ${toneClasses[c.status]}`}>{LABEL[c.status]}</span>
          </li>
        ))}
        {!checks && <li className="text-sm text-slate-500">Loading…</li>}
      </ul>
    </div>
  )
}
