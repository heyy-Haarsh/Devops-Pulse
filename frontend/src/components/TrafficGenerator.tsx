import { useState } from 'react'
import { AlertOctagon, Hourglass, Send, Zap } from 'lucide-react'

type Mode = 'normal' | 'errors' | 'slow'

const MODES: Record<Mode, { label: string; desc: string; path: string; count: number; icon: typeof Send; cls: string }> = {
  normal: {
    label: 'Normal traffic',
    desc: '100 fast requests',
    path: '/api/demo/ok',
    count: 100,
    icon: Send,
    cls: 'border-cyan-500/40 hover:bg-cyan-500/10 text-cyan-300',
  },
  errors: {
    label: 'Error burst',
    desc: '40 HTTP 500 responses',
    path: '/api/demo/error',
    count: 40,
    icon: AlertOctagon,
    cls: 'border-rose-500/40 hover:bg-rose-500/10 text-rose-300',
  },
  slow: {
    label: 'Latency spike',
    desc: '20 requests × 900 ms',
    path: '/api/demo/slow?ms=900',
    count: 20,
    icon: Hourglass,
    cls: 'border-amber-500/40 hover:bg-amber-500/10 text-amber-300',
  },
}

async function fire(path: string, count: number, concurrency = 10) {
  let sent = 0
  const worker = async () => {
    while (sent < count) {
      sent++
      await fetch(path).catch(() => undefined)
    }
  }
  await Promise.all(Array.from({ length: concurrency }, worker))
}

export function TrafficGenerator() {
  const [running, setRunning] = useState<Mode | null>(null)
  const [last, setLast] = useState<string>('')

  const run = async (mode: Mode) => {
    const m = MODES[mode]
    setRunning(mode)
    const started = performance.now()
    await fire(m.path, m.count)
    setLast(`${m.label}: sent ${m.count} requests in ${((performance.now() - started) / 1000).toFixed(1)}s`)
    setRunning(null)
  }

  return (
    <section id="traffic" className="card">
      <h2 className="card-title">
        <Zap size={16} /> Traffic Generator
      </h2>
      <p className="mb-4 text-xs text-slate-500">
        Sends real HTTP requests through the Kubernetes Service so you can watch Prometheus, Grafana and this dashboard
        react. Only the generated requests are affected — nothing is crashed or reconfigured.
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {(Object.keys(MODES) as Mode[]).map((key) => {
          const m = MODES[key]
          return (
            <button
              key={key}
              disabled={running !== null}
              onClick={() => run(key)}
              className={`flex items-center gap-3 rounded-lg border bg-slate-950/50 p-3 text-left transition disabled:opacity-50 ${m.cls}`}
            >
              <m.icon size={18} className={running === key ? 'animate-pulse' : ''} />
              <div>
                <div className="text-sm font-semibold">{running === key ? 'Sending…' : m.label}</div>
                <div className="text-xs text-slate-500">{m.desc}</div>
              </div>
            </button>
          )
        })}
      </div>
      {last && <div className="mt-3 text-xs text-slate-400">{last}</div>}
    </section>
  )
}
