import { AlertTriangle, CheckCircle2, MinusCircle, XCircle } from 'lucide-react'
import type { CheckStatus } from '../api'

export const toneClasses: Record<CheckStatus, string> = {
  ok: 'text-emerald-400',
  warn: 'text-amber-400',
  error: 'text-rose-400',
  off: 'text-slate-500',
}

export function StatusIcon({ status, size = 18 }: { status: CheckStatus; size?: number }) {
  const cls = toneClasses[status]
  if (status === 'ok') return <CheckCircle2 size={size} className={cls} />
  if (status === 'warn') return <AlertTriangle size={size} className={cls} />
  if (status === 'error') return <XCircle size={size} className={cls} />
  return <MinusCircle size={size} className={cls} />
}

export function PulseDot({ status }: { status: CheckStatus }) {
  const color = {
    ok: 'bg-emerald-400',
    warn: 'bg-amber-400',
    error: 'bg-rose-500',
    off: 'bg-slate-500',
  }[status]
  return (
    <span className="relative flex h-2.5 w-2.5">
      {status !== 'off' && (
        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${color}`} />
      )}
      <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${color}`} />
    </span>
  )
}
