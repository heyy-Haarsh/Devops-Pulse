import { describe, expect, it } from 'vitest'
import { detectAnomalies } from '../anomalies'
import type { KubernetesInfo, MetricsSummary } from '../api'

const metrics = (overrides: Partial<MetricsSummary> = {}): MetricsSummary => ({
  source: 'prometheus',
  request_rate_per_second: 5,
  average_latency_ms: 12,
  p95_latency_ms: 40,
  error_rate_percent: 0,
  active_requests: 1,
  uptime_seconds: 100,
  uptime_human: '1m 40s',
  total_requests: 500,
  total_errors: 0,
  instances_up: 2,
  served_by: 'pod-a',
  timestamp: '',
  ...overrides,
})

const k8s = (ready: number, desired: number, status = 'Running'): KubernetesInfo => ({
  mode: 'kubernetes',
  connected: true,
  errors: [],
  namespace: 'devops-pulse',
  deployment: { name: 'devops-pulse', replicas_desired: desired, status: 'Available' },
  pods: Array.from({ length: desired }, (_, i) => ({
    name: `pod-${i}`,
    status: i < ready ? 'Running' : status,
    ready: i < ready,
    restarts: 0,
    node: 'minikube',
    ip: '10.0.0.1',
    image: 'devops-pulse:1',
    age_seconds: 10,
    is_current: false,
  })),
  service: { name: 'svc', status: 'Active' },
  config_map: 'cm',
  served_by: 'pod-0',
})

describe('detectAnomalies', () => {
  it('reports nothing for a healthy system', () => {
    expect(detectAnomalies(metrics(), k8s(2, 2))).toEqual([])
  })

  it('flags a high error rate', () => {
    const out = detectAnomalies(metrics({ error_rate_percent: 12 }))
    expect(out[0].level).toBe('error')
    expect(out[0].message).toMatch(/Error rate/)
  })

  it('flags high latency', () => {
    expect(detectAnomalies(metrics({ p95_latency_ms: 900 }))[0].message).toMatch(/Latency/)
  })

  it('flags pods that are not ready', () => {
    const out = detectAnomalies(metrics(), k8s(1, 3, 'CrashLoopBackOff'))
    expect(out.some((a) => a.message.includes('1/3 pods ready'))).toBe(true)
    expect(out.some((a) => a.message.includes('CrashLoopBackOff'))).toBe(true)
  })

  it('flags an unreachable backend', () => {
    expect(detectAnomalies(undefined, undefined, undefined, false)[0].level).toBe('error')
  })
})
