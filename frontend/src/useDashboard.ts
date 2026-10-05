import { useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  DeploymentInfo,
  KubernetesInfo,
  MetricsSummary,
  MonitoringInfo,
  StatusResponse,
  SystemEvent,
} from './api'

export const POLL_INTERVAL_MS = 5000
const HISTORY_POINTS = 36 // 3 minutes at 5 s

export interface HistoryPoint {
  time: string
  requestRate: number
  errorRate: number
  avgLatency: number
  p95Latency: number | null
  replicas: number
}

export interface DashboardData {
  status?: StatusResponse
  metrics?: MetricsSummary
  deployment?: DeploymentInfo
  kubernetes?: KubernetesInfo
  events: SystemEvent[]
  monitoring?: MonitoringInfo
  history: HistoryPoint[]
  connected: boolean
  lastUpdated?: Date
  refresh: () => void
}

export function useDashboard(): DashboardData {
  const [state, setState] = useState<Omit<DashboardData, 'refresh'>>({
    events: [],
    history: [],
    connected: true,
  })
  const mounted = useRef(true)

  const load = useCallback(async () => {
    const [status, metrics, deployment, kubernetes, events, monitoring] = await Promise.allSettled([
      api.status(),
      api.metrics(),
      api.deployment(),
      api.kubernetes(),
      api.events(),
      api.monitoring(),
    ])
    if (!mounted.current) return

    const val = <T,>(r: PromiseSettledResult<T>) => (r.status === 'fulfilled' ? r.value : undefined)
    const m = val(metrics)
    const k = val(kubernetes)

    setState((prev) => {
      const history = m
        ? [
            ...prev.history,
            {
              time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
              requestRate: m.request_rate_per_second,
              errorRate: m.error_rate_percent,
              avgLatency: m.average_latency_ms,
              p95Latency: m.p95_latency_ms,
              replicas: k ? k.pods.filter((p) => p.ready).length : m.instances_up,
            },
          ].slice(-HISTORY_POINTS)
        : prev.history

      return {
        status: val(status) ?? prev.status,
        metrics: m ?? prev.metrics,
        deployment: val(deployment) ?? prev.deployment,
        kubernetes: k ?? prev.kubernetes,
        events: val(events) ?? prev.events,
        monitoring: val(monitoring) ?? prev.monitoring,
        history,
        connected: status.status === 'fulfilled',
        lastUpdated: status.status === 'fulfilled' ? new Date() : prev.lastUpdated,
      }
    })
  }, [])

  useEffect(() => {
    mounted.current = true
    load()
    const id = setInterval(load, POLL_INTERVAL_MS)
    return () => {
      mounted.current = false
      clearInterval(id)
    }
  }, [load])

  return { ...state, refresh: load }
}
