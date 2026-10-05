import { Boxes, Network, Server } from 'lucide-react'
import type { KubernetesInfo } from '../api'

function formatAge(seconds: number | null) {
  if (seconds === null) return '-'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${Math.floor(seconds / 3600)}h${Math.floor((seconds % 3600) / 60)}m`
}

function statusColor(status: string, ready: boolean) {
  if (status === 'Running' && ready) return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
  if (status === 'Running' || status === 'Pending' || status === 'ContainerCreating' || status === 'Terminating')
    return 'bg-amber-500/15 text-amber-300 border-amber-500/30'
  return 'bg-rose-500/15 text-rose-300 border-rose-500/40'
}

export function KubernetesPanel({ k8s }: { k8s?: KubernetesInfo }) {
  const isLocal = k8s?.mode === 'local'
  const dep = k8s?.deployment
  const svc = k8s?.service

  return (
    <section id="kubernetes" className="card">
      <h2 className="card-title justify-between">
        <span className="flex items-center gap-2">
          <Boxes size={16} /> Kubernetes Workload
        </span>
        {k8s && (
          <span className="rounded-full border border-slate-700 px-2 py-0.5 font-mono text-[11px] normal-case text-slate-400">
            {isLocal ? 'local mode' : `namespace/${k8s.namespace}`}
          </span>
        )}
      </h2>

      {isLocal && (
        <p className="mb-4 rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-400">
          The backend is not running inside a Kubernetes Pod, so it is showing this local process only. Deploy with{' '}
          <code className="text-cyan-300">kubectl apply -f k8s/</code> to see live Pods, replicas and the Service.
        </p>
      )}

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="rounded-lg bg-slate-950/50 p-3">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Server size={14} /> Deployment
          </div>
          <div className="mt-1 font-mono text-sm text-white">{dep?.name ?? '…'}</div>
          <div className="text-xs text-slate-400">
            {dep?.status} · {dep?.strategy ?? '-'}
          </div>
        </div>
        <div className="rounded-lg bg-slate-950/50 p-3">
          <div className="text-xs text-slate-500">Replicas (ready / desired)</div>
          <div className="mt-1 text-2xl font-bold text-white">
            {dep?.replicas_ready ?? 0}
            <span className="text-slate-500"> / {dep?.replicas_desired ?? 0}</span>
          </div>
          <div className="mt-1 flex gap-1">
            {Array.from({ length: dep?.replicas_desired ?? 0 }).map((_, i) => (
              <span
                key={i}
                className={`h-1.5 flex-1 rounded-full ${i < (dep?.replicas_ready ?? 0) ? 'bg-emerald-400' : 'bg-slate-700'}`}
              />
            ))}
          </div>
        </div>
        <div className="rounded-lg bg-slate-950/50 p-3">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Network size={14} /> Service
          </div>
          <div className="mt-1 font-mono text-sm text-white">{svc?.name ?? '…'}</div>
          <div className="text-xs text-slate-400">
            {svc?.type ?? '-'}
            {svc?.port ? ` · ${svc.port}→${svc.target_port}` : ''}
            {svc?.node_port ? ` · nodePort ${svc.node_port}` : ''} · {svc?.endpoints ?? 0} endpoints
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs uppercase tracking-wider text-slate-500">
            <tr>
              <th className="pb-2 font-medium">Pod</th>
              <th className="pb-2 font-medium">Status</th>
              <th className="pb-2 font-medium">Ready</th>
              <th className="pb-2 font-medium">Restarts</th>
              <th className="pb-2 font-medium">IP</th>
              <th className="pb-2 font-medium">Node</th>
              <th className="pb-2 font-medium">Age</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {(k8s?.pods ?? []).map((p) => (
              <tr key={p.name} className="text-slate-300">
                <td className="py-2 pr-3 font-mono text-xs">
                  {p.name}
                  {p.is_current && (
                    <span className="ml-2 rounded bg-cyan-500/15 px-1.5 py-0.5 text-[10px] text-cyan-300">serving you</span>
                  )}
                </td>
                <td className="py-2 pr-3">
                  <span className={`rounded-full border px-2 py-0.5 text-xs ${statusColor(p.status, p.ready)}`}>{p.status}</span>
                </td>
                <td className="py-2 pr-3">{p.ready ? '1/1' : '0/1'}</td>
                <td className={`py-2 pr-3 ${p.restarts > 0 ? 'text-amber-300' : ''}`}>{p.restarts}</td>
                <td className="py-2 pr-3 font-mono text-xs">{p.ip}</td>
                <td className="py-2 pr-3 text-xs">{p.node}</td>
                <td className="py-2 text-xs">{formatAge(p.age_seconds)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
