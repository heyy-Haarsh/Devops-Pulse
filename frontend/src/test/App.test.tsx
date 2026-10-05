import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from '../App'

const responses: Record<string, unknown> = {
  '/api/status': {
    status: 'healthy',
    overall: 'healthy',
    health_score: 100,
    version: '1.2.3',
    environment: 'test',
    uptime_seconds: 42,
    served_by: 'devops-pulse-abc',
    diagnostics: [{ name: 'Backend API', status: 'ok', detail: 'Serving' }],
  },
  '/api/metrics-summary': {
    source: 'prometheus',
    request_rate_per_second: 3.5,
    average_latency_ms: 10,
    p95_latency_ms: 25,
    error_rate_percent: 0,
    active_requests: 1,
    uptime_seconds: 42,
    uptime_human: '42s',
    total_requests: 1234,
    total_errors: 0,
    instances_up: 3,
    served_by: 'devops-pulse-abc',
    timestamp: '',
  },
  '/api/deployment': {
    version: '1.2.3',
    build_number: '17',
    git_commit: 'abcdef1234567',
    build_time: null,
    image: 'devops-pulse:17',
    status: 'Running',
    replicas: { desired: 3, available: 3, ready: 3, updated: 3 },
    environment: 'test',
    strategy: 'RollingUpdate',
    namespace: 'devops-pulse',
    mode: 'kubernetes',
  },
  '/api/kubernetes': {
    mode: 'kubernetes',
    connected: true,
    errors: [],
    namespace: 'devops-pulse',
    deployment: { name: 'devops-pulse', replicas_desired: 3, replicas_ready: 3, status: 'Available' },
    pods: ['a', 'b', 'c'].map((s) => ({
      name: `devops-pulse-${s}`,
      status: 'Running',
      ready: true,
      restarts: 0,
      node: 'minikube',
      ip: '10.0.0.1',
      image: 'devops-pulse:17',
      age_seconds: 30,
      is_current: s === 'a',
    })),
    service: { name: 'devops-pulse-service', type: 'NodePort', endpoints: 3, status: 'Active' },
    config_map: 'devops-pulse-config',
    served_by: 'devops-pulse-a',
  },
  '/api/events': { events: [] },
  '/api/monitoring': {
    prometheus: { status: 'healthy', url: '#', targets_up: 3, targets_total: 3, targets: [], alerts: [] },
    grafana: { status: 'healthy', url: '#', dashboards: 1, datasource_ok: true },
  },
}

afterEach(() => vi.restoreAllMocks())

describe('App', () => {
  it('renders live data from the backend', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const body = responses[String(input)]
      return new Response(JSON.stringify(body), { status: body ? 200 : 404 })
    })

    render(<App />)

    await waitFor(() => expect(screen.getByText('3 / 3')).toBeInTheDocument())
    expect(screen.getByText('Build #17')).toBeInTheDocument()
    expect(screen.getByText('abcdef1')).toBeInTheDocument()
    expect(screen.getAllByText('3/3 targets UP').length).toBeGreaterThan(0)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows an anomaly banner when the backend is unreachable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'))
    render(<App />)
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Backend API unreachable'))
  })
})
