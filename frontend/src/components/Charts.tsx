import { Activity, Timer } from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { THRESHOLDS } from '../anomalies'
import type { HistoryPoint } from '../useDashboard'

const axis = { stroke: '#475569', fontSize: 11, tickLine: false, axisLine: false }
const tooltipStyle = {
  contentStyle: { background: '#0f172a', border: '1px solid #334155', borderRadius: 8, fontSize: 12 },
  labelStyle: { color: '#94a3b8' },
}

function Empty() {
  return <div className="flex h-56 items-center justify-center text-sm text-slate-500">Collecting samples…</div>
}

export function TrafficChart({ history, source }: { history: HistoryPoint[]; source?: string }) {
  return (
    <div className="card">
      <h2 className="card-title justify-between">
        <span className="flex items-center gap-2">
          <Activity size={16} /> Request &amp; Error Rate
        </span>
        <span className="text-[10px] font-normal normal-case text-slate-500">source: {source ?? '…'}</span>
      </h2>
      {history.length < 2 ? (
        <Empty />
      ) : (
        <ResponsiveContainer width="100%" height={224}>
          <AreaChart data={history} margin={{ left: -18, right: 8 }}>
            <defs>
              <linearGradient id="rps" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.45} />
                <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="err" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1e293b" vertical={false} />
            <XAxis dataKey="time" {...axis} minTickGap={40} />
            <YAxis yAxisId="rps" {...axis} />
            <YAxis yAxisId="err" orientation="right" {...axis} unit="%" />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <ReferenceLine yAxisId="err" y={THRESHOLDS.errorRatePercent} stroke="#f43f5e" strokeDasharray="4 4" />
            <Area yAxisId="rps" type="monotone" dataKey="requestRate" name="req/s" stroke="#22d3ee" fill="url(#rps)" strokeWidth={2} isAnimationActive={false} />
            <Area yAxisId="err" type="monotone" dataKey="errorRate" name="error %" stroke="#f43f5e" fill="url(#err)" strokeWidth={2} isAnimationActive={false} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

export function LatencyChart({ history }: { history: HistoryPoint[] }) {
  return (
    <div className="card">
      <h2 className="card-title">
        <Timer size={16} /> Request Latency (ms)
      </h2>
      {history.length < 2 ? (
        <Empty />
      ) : (
        <ResponsiveContainer width="100%" height={224}>
          <LineChart data={history} margin={{ left: -18, right: 8 }}>
            <CartesianGrid stroke="#1e293b" vertical={false} />
            <XAxis dataKey="time" {...axis} minTickGap={40} />
            <YAxis {...axis} />
            <Tooltip {...tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <ReferenceLine y={THRESHOLDS.p95LatencyMs} stroke="#f59e0b" strokeDasharray="4 4" />
            <Line type="monotone" dataKey="avgLatency" name="average" stroke="#a78bfa" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line type="monotone" dataKey="p95Latency" name="p95" stroke="#f59e0b" strokeWidth={2} dot={false} isAnimationActive={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
