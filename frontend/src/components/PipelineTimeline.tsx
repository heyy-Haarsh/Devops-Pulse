import { BarChart3, Boxes, ChevronRight, Container, Flame, GitCommit, Workflow } from 'lucide-react'
import type { CheckStatus, DeploymentInfo, KubernetesInfo, MonitoringInfo } from '../api'
import { StatusIcon } from './StatusDot'

interface Props {
  deployment?: DeploymentInfo
  kubernetes?: KubernetesInfo
  monitoring?: MonitoringInfo
}

interface Stage {
  name: string
  icon: typeof GitCommit
  title: string
  detail: string
  status: CheckStatus
}

export function PipelineTimeline({ deployment, kubernetes, monitoring }: Props) {
  const commit = deployment?.git_commit ?? 'unknown'
  const build = deployment?.build_number ?? 'local'
  const isK8s = kubernetes?.mode === 'kubernetes'
  const desired = kubernetes?.deployment.replicas_desired ?? 0
  const ready = kubernetes?.pods.filter((p) => p.ready).length ?? 0
  const prom = monitoring?.prometheus
  const graf = monitoring?.grafana

  const stages: Stage[] = [
    {
      name: 'Git',
      icon: GitCommit,
      title: commit === 'unknown' ? 'Working copy' : commit.slice(0, 7),
      detail: 'Source commit',
      status: commit === 'unknown' ? 'off' : 'ok',
    },
    {
      name: 'Jenkins',
      icon: Workflow,
      title: build === 'local' ? 'Manual build' : `Build #${build}`,
      detail: deployment?.build_time ? new Date(deployment.build_time).toLocaleString() : 'CI/CD pipeline',
      status: build === 'local' ? 'off' : 'ok',
    },
    {
      name: 'Docker',
      icon: Container,
      title: deployment?.image ?? '…',
      detail: 'Container image',
      status: deployment ? 'ok' : 'off',
    },
    {
      name: 'Kubernetes',
      icon: Boxes,
      title: isK8s ? `${ready}/${desired} pods ready` : 'Not in cluster',
      detail: isK8s ? `${kubernetes?.namespace} · ${kubernetes?.deployment.status}` : 'Local process',
      status: !isK8s ? 'off' : ready >= desired && desired > 0 ? 'ok' : ready > 0 ? 'warn' : 'error',
    },
    {
      name: 'Prometheus',
      icon: Flame,
      title:
        prom?.status === 'healthy' ? `${prom.targets_up}/${prom.targets_total} targets UP` : prom?.status ?? '…',
      detail: prom?.scrape_interval ? `Scrape every ${prom.scrape_interval}` : 'Metrics scraping',
      status:
        prom?.status === 'healthy'
          ? prom.targets_total && prom.targets_up === prom.targets_total
            ? 'ok'
            : 'warn'
          : prom?.status === 'not_configured'
            ? 'off'
            : 'error',
    },
    {
      name: 'Grafana',
      icon: BarChart3,
      title: graf?.status === 'healthy' ? (graf.datasource_ok ? 'Datasource OK' : 'Datasource error') : graf?.status ?? '…',
      detail: graf?.dashboards !== undefined ? `${graf.dashboards} dashboard(s)` : 'Visualization',
      status:
        graf?.status === 'healthy' ? (graf.datasource_ok ? 'ok' : 'warn') : graf?.status === 'not_configured' ? 'off' : 'error',
    },
  ]

  return (
    <section id="pipeline" className="card">
      <h2 className="card-title">
        <Workflow size={16} /> Delivery Pipeline — Build → Ship → Deploy → Scale → Observe
      </h2>
      <div className="flex flex-col gap-3 xl:flex-row xl:items-stretch">
        {stages.map((stage, i) => (
          <div key={stage.name} className="flex flex-1 flex-col items-stretch gap-3 xl:flex-row xl:items-center">
            <div
              className={`flex-1 rounded-lg border p-3 ${
                stage.status === 'ok'
                  ? 'border-emerald-500/30 bg-emerald-500/5'
                  : stage.status === 'warn'
                    ? 'border-amber-500/40 bg-amber-500/5'
                    : stage.status === 'error'
                      ? 'border-rose-500/50 bg-rose-500/10'
                      : 'border-slate-800 bg-slate-900'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-white">
                  <stage.icon size={16} className="text-cyan-400" />
                  {stage.name}
                </div>
                <StatusIcon status={stage.status} size={16} />
              </div>
              <div className="mt-2 truncate font-mono text-xs text-slate-200" title={stage.title}>
                {stage.title}
              </div>
              <div className="mt-0.5 truncate text-xs text-slate-500">{stage.detail}</div>
            </div>
            {i < stages.length - 1 && (
              <ChevronRight className="mx-auto shrink-0 rotate-90 text-slate-600 xl:rotate-0" size={18} />
            )}
          </div>
        ))}
      </div>
    </section>
  )
}
