import { AlertTriangle, Clock, Gauge, HeartPulse, Layers, RefreshCw, Timer, TrendingUp, XOctagon } from 'lucide-react'
import type { CheckStatus } from './api'
import { detectAnomalies, THRESHOLDS } from './anomalies'
import { LatencyChart, TrafficChart } from './components/Charts'
import { Diagnostics } from './components/Diagnostics'
import { EventsFeed } from './components/EventsFeed'
import { KubernetesPanel } from './components/KubernetesPanel'
import { MetricCard } from './components/MetricCard'
import { MonitoringPanel } from './components/MonitoringPanel'
import { PipelineTimeline } from './components/PipelineTimeline'
import { Sidebar } from './components/Sidebar'
import { PulseDot } from './components/StatusDot'
import { TrafficGenerator } from './components/TrafficGenerator'
import { useDashboard } from './useDashboard'

export default function App() {
  const d = useDashboard()
  const { status, metrics, deployment, kubernetes, monitoring } = d
  const anomalies = detectAnomalies(metrics, kubernetes, monitoring, d.connected)

  const overall: CheckStatus = !d.connected
    ? 'error'
    : anomalies.some((a) => a.level === 'error') || status?.overall === 'critical'
      ? 'error'
      : anomalies.length || status?.overall === 'degraded'
        ? 'warn'
        : 'ok'

  const desired = kubernetes?.deployment.replicas_desired ?? deployment?.replicas.desired ?? 0
  const ready = kubernetes ? kubernetes.pods.filter((p) => p.ready).length : 0
  const latency = metrics?.p95_latency_ms ?? metrics?.average_latency_ms ?? 0

  return (
    <div className="min-h-screen bg-[radial-gradient(ellipse_at_top,_#0e2438_0%,_#020617_55%)]">
      <Sidebar overall={overall} version={status?.version} environment={status?.environment} />

      <main className="lg:pl-60">
        <header className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950/80 px-6 py-4 backdrop-blur">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-xl font-bold text-white">Platform Overview</h1>
              <p className="text-xs text-slate-500">
                Git → Jenkins → Docker → Kubernetes → Prometheus → Grafana
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5">
                <PulseDot status={overall} />
                <span className="font-medium text-slate-200">
                  {overall === 'ok' ? 'Healthy' : overall === 'warn' ? 'Degraded' : 'Unhealthy'}
                </span>
              </span>
              {metrics?.served_by && (
                <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-slate-400" title="Pod that answered the last API call">
                  served by <span className="font-mono text-cyan-300">{metrics.served_by}</span>
                </span>
              )}
              <button
                onClick={d.refresh}
                className="flex items-center gap-1.5 rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-slate-400 transition hover:text-white"
              >
                <RefreshCw size={13} />
                {d.lastUpdated ? d.lastUpdated.toLocaleTimeString() : 'Loading'}
              </button>
            </div>
          </div>
        </header>

        <div className="space-y-6 p-6">
          {anomalies.length > 0 && (
            <div
              role="alert"
              className={`rounded-xl border p-4 ${
                overall === 'error' ? 'border-rose-500/50 bg-rose-500/10' : 'border-amber-500/50 bg-amber-500/10'
              }`}
            >
              <div className="mb-1 flex items-center gap-2 font-semibold text-white">
                {overall === 'error' ? <XOctagon size={18} className="text-rose-400" /> : <AlertTriangle size={18} className="text-amber-400" />}
                Anomaly detected
              </div>
              <ul className="ml-7 list-disc space-y-0.5 text-sm text-slate-300">
                {anomalies.map((a) => (
                  <li key={a.message}>{a.message}</li>
                ))}
              </ul>
            </div>
          )}

          <section id="overview" className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
            <MetricCard
              label="System Health"
              value={status ? `${status.health_score}%` : '…'}
              sub={status ? `${status.diagnostics.filter((c) => c.status === 'ok').length} checks passing` : undefined}
              icon={HeartPulse}
              tone={overall}
            />
            <MetricCard
              label="Active Replicas"
              value={kubernetes?.mode === 'kubernetes' ? `${ready} / ${desired}` : '1 (local)'}
              sub={kubernetes?.mode === 'kubernetes' ? `Prometheus sees ${metrics?.instances_up ?? '…'} instance(s)` : 'Not in a cluster'}
              icon={Layers}
              tone={kubernetes?.mode === 'kubernetes' && ready < desired ? (ready === 0 ? 'error' : 'warn') : 'ok'}
            />
            <MetricCard
              label="Request Rate"
              value={metrics ? `${metrics.request_rate_per_second.toFixed(2)} /s` : '…'}
              sub={metrics ? `${metrics.total_requests.toLocaleString()} total` : undefined}
              icon={TrendingUp}
            />
            <MetricCard
              label="Latency"
              value={metrics ? `${latency.toFixed(1)} ms` : '…'}
              sub={metrics?.p95_latency_ms != null ? `p95 · avg ${metrics.average_latency_ms.toFixed(1)} ms` : 'average'}
              icon={Timer}
              tone={latency > THRESHOLDS.p95LatencyMs ? 'warn' : 'ok'}
            />
            <MetricCard
              label="Error Rate"
              value={metrics ? `${metrics.error_rate_percent.toFixed(2)}%` : '…'}
              sub={metrics ? `${metrics.total_errors.toLocaleString()} errors total` : undefined}
              icon={Gauge}
              tone={metrics && metrics.error_rate_percent > THRESHOLDS.errorRatePercent ? 'error' : 'ok'}
            />
            <MetricCard
              label="Uptime"
              value={metrics?.uptime_human ?? '…'}
              sub={deployment ? `v${deployment.version} · ${deployment.image}` : undefined}
              icon={Clock}
            />
          </section>

          <PipelineTimeline deployment={deployment} kubernetes={kubernetes} monitoring={monitoring} />

          <section id="monitoring" className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <TrafficChart history={d.history} source={metrics?.source} />
            <LatencyChart history={d.history} />
          </section>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <KubernetesPanel k8s={kubernetes} />
            </div>
            <Diagnostics checks={status?.diagnostics} />
          </div>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <EventsFeed events={d.events} />
            </div>
            <MonitoringPanel monitoring={monitoring} />
          </div>

          <TrafficGenerator />

          <footer className="pb-4 text-center text-xs text-slate-600">
            DevOps Pulse · data refreshes every 5 s from the FastAPI backend
            {metrics?.source === 'prometheus' ? ' (cluster-wide metrics via Prometheus)' : ''}
          </footer>
        </div>
      </main>
    </div>
  )
}