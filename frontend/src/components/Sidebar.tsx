import { Activity, Boxes, GitBranch, Gauge, LayoutDashboard, ListTree, Zap } from 'lucide-react'
import type { CheckStatus } from '../api'
import { PulseDot } from './StatusDot'

const NAV = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'pipeline', label: 'Pipeline', icon: GitBranch },
  { id: 'monitoring', label: 'Monitoring', icon: Activity },
  { id: 'kubernetes', label: 'Kubernetes', icon: Boxes },
  { id: 'events', label: 'Events', icon: ListTree },
  { id: 'traffic', label: 'Traffic Generator', icon: Zap },
]

interface Props {
  overall: CheckStatus
  version?: string
  environment?: string
}

export function Sidebar({ overall, version, environment }: Props) {
  return (
    <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 flex-col border-r border-slate-800 bg-slate-950/95 lg:flex">
      <div className="flex items-center gap-3 px-6 py-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-400 to-indigo-500 shadow-lg shadow-cyan-500/30">
          <Gauge size={22} className="text-slate-950" />
        </div>
        <div>
          <div className="text-lg font-bold tracking-tight text-white">DevOps Pulse</div>
          <div className="text-xs text-slate-500">Build · Ship · Deploy · Observe</div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {NAV.map(({ id, label, icon: Icon }) => (
          <a
            key={id}
            href={`#${id}`}
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-400 transition hover:bg-slate-800/70 hover:text-white"
          >
            <Icon size={17} />
            {label}
          </a>
        ))}
      </nav>

      <div className="m-3 rounded-lg border border-slate-800 bg-slate-900/70 p-4 text-xs">
        <div className="mb-2 flex items-center gap-2 font-medium text-slate-300">
          <PulseDot status={overall} />
          {overall === 'ok' ? 'All systems operational' : overall === 'warn' ? 'Degraded' : 'Unhealthy'}
        </div>
        <div className="space-y-1 text-slate-500">
          <div>
            Version <span className="font-mono text-slate-300">v{version ?? '…'}</span>
          </div>
          <div>
            Env <span className="font-mono text-slate-300">{environment ?? '…'}</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
