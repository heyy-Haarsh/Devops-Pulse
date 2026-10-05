import type { LucideIcon } from 'lucide-react'
import type { CheckStatus } from '../api'

interface Props {
  label: string
  value: string
  sub?: string
  icon: LucideIcon
  tone?: CheckStatus
}

const toneStyles: Record<CheckStatus, { ring: string; icon: string }> = {
  ok: { ring: 'border-slate-800', icon: 'bg-cyan-500/10 text-cyan-400' },
  warn: { ring: 'border-amber-500/50 shadow-amber-500/10', icon: 'bg-amber-500/10 text-amber-400' },
  error: { ring: 'border-rose-500/60 shadow-rose-500/20', icon: 'bg-rose-500/10 text-rose-400' },
  off: { ring: 'border-slate-800', icon: 'bg-slate-700/30 text-slate-400' },
}

export function MetricCard({ label, value, sub, icon: Icon, tone = 'ok' }: Props) {
  const s = toneStyles[tone]
  return (
    <div className={`card flex items-start justify-between transition-colors ${s.ring}`} data-testid={`metric-${label}`}>
      <div className="min-w-0">
        <div className="text-xs font-medium uppercase tracking-wider text-slate-500">{label}</div>
        <div className="mt-2 truncate text-2xl font-bold text-white">{value}</div>
        {sub && <div className="mt-1 truncate text-xs text-slate-500">{sub}</div>}
      </div>
      <div className={`rounded-lg p-2.5 ${s.icon}`}>
        <Icon size={20} />
      </div>
    </div>
  )
}
