import type { KubernetesInfo, MetricsSummary, MonitoringInfo } from './api'

/** Thresholds match the Prometheus alert rules in monitoring/prometheus/alert-rules.yml */
export const THRESHOLDS = {
  errorRatePercent: 5,
  p95LatencyMs: 500,
}

export interface Anomaly {
  level: 'warn' | 'error'
  message: string
}

export function detectAnomalies(
  metrics?: MetricsSummary,
  kubernetes?: KubernetesInfo,
  monitoring?: MonitoringInfo,
  connected = true,
): Anomaly[] {
  const out: Anomaly[] = []
  if (!connected) {
    out.push({ level: 'error', message: 'Backend API unreachable — dashboard is showing last known data' })
    return out
  }

  if (metrics && metrics.error_rate_percent > THRESHOLDS.errorRatePercent) {
    out.push({
      level: 'error',
      message: `Error rate ${metrics.error_rate_percent.toFixed(1)}% exceeds ${THRESHOLDS.errorRatePercent}%`,
    })
  }
  const latency = metrics?.p95_latency_ms ?? metrics?.average_latency_ms
  if (latency !== undefined && latency !== null && latency > THRESHOLDS.p95LatencyMs) {
    out.push({ level: 'warn', message: `Latency ${latency.toFixed(0)} ms exceeds ${THRESHOLDS.p95LatencyMs} ms` })
  }

  if (kubernetes?.mode === 'kubernetes') {
    const desired = kubernetes.deployment.replicas_desired ?? 0
    const ready = kubernetes.pods.filter((p) => p.ready).length
    if (ready < desired) {
      out.push({ level: ready === 0 ? 'error' : 'warn', message: `Only ${ready}/${desired} pods ready` })
    }
    for (const pod of kubernetes.pods) {
      if (!['Running', 'Terminating'].includes(pod.status)) {
        out.push({ level: 'error', message: `Pod ${pod.name} is ${pod.status}` })
      }
    }
  }

  const prom = monitoring?.prometheus
  if (prom?.status === 'healthy' && prom.targets_total && (prom.targets_up ?? 0) < prom.targets_total) {
    out.push({ level: 'error', message: `Prometheus: ${prom.targets_up}/${prom.targets_total} scrape targets UP` })
  }
  for (const alert of prom?.alerts ?? []) {
    if (alert.state === 'firing') {
      out.push({ level: alert.severity === 'critical' ? 'error' : 'warn', message: `Alert ${alert.name}: ${alert.summary}` })
    }
  }
  return out
}
