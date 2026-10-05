export type CheckStatus = 'ok' | 'warn' | 'error' | 'off'

export interface Diagnostic {
  name: string
  status: CheckStatus
  detail: string
}

export interface StatusResponse {
  status: string
  overall: 'healthy' | 'degraded' | 'critical'
  health_score: number
  version: string
  environment: string
  uptime_seconds: number
  served_by: string
  diagnostics: Diagnostic[]
}

export interface MetricsSummary {
  source: 'prometheus' | 'local'
  request_rate_per_second: number
  average_latency_ms: number
  p95_latency_ms: number | null
  error_rate_percent: number
  active_requests: number
  uptime_seconds: number
  uptime_human: string
  total_requests: number
  total_errors: number
  instances_up: number
  served_by: string
  timestamp: string
}

export interface DeploymentInfo {
  version: string
  build_number: string
  git_commit: string
  build_time: string | null
  image: string
  status: string
  replicas: { desired: number; available: number; ready: number; updated: number }
  environment: string
  strategy: string
  namespace: string
  mode: 'kubernetes' | 'local'
}

export interface Pod {
  name: string
  status: string
  ready: boolean
  restarts: number
  node: string
  ip: string
  image: string
  age_seconds: number | null
  is_current: boolean
}

export interface KubernetesInfo {
  mode: 'kubernetes' | 'local'
  connected: boolean
  errors: string[]
  namespace: string
  deployment: {
    name: string
    replicas_desired?: number
    replicas_ready?: number
    replicas_available?: number
    status: string
    strategy?: string
  }
  pods: Pod[]
  service: {
    name: string
    type?: string
    cluster_ip?: string
    port?: number
    target_port?: number | string
    node_port?: number
    endpoints?: number
    status: string
  }
  config_map: string
  served_by: string
}

export interface SystemEvent {
  id?: number
  type: string
  severity: 'success' | 'info' | 'warning' | 'error'
  message: string
  timestamp: string
  reason?: string
  object?: string
  count?: number
}

export interface PromTarget {
  instance: string
  pod?: string
  health: string
  last_scrape: string
  last_error: string
}

export interface Alert {
  name: string
  state: string
  severity: string
  summary: string
}

export interface MonitoringInfo {
  prometheus: {
    status: string
    url: string
    targets_up?: number
    targets_total?: number
    targets?: PromTarget[]
    scrape_interval?: string | null
    alerts?: Alert[]
  }
  grafana: {
    status: string
    url: string
    version?: string
    dashboards?: number
    datasource_ok?: boolean
  }
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(path, { headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${path} → HTTP ${res.status}`)
  return res.json() as Promise<T>
}

export const api = {
  status: () => getJSON<StatusResponse>('/api/status'),
  metrics: () => getJSON<MetricsSummary>('/api/metrics-summary'),
  deployment: () => getJSON<DeploymentInfo>('/api/deployment'),
  kubernetes: () => getJSON<KubernetesInfo>('/api/kubernetes'),
  events: () => getJSON<{ events: SystemEvent[] }>('/api/events').then((r) => r.events),
  monitoring: () => getJSON<MonitoringInfo>('/api/monitoring'),
}
