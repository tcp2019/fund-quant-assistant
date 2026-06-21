import type { Signal } from '../types'

interface SignalCardProps {
  signal: Signal
}

const SIGNAL_TYPE_LABELS: Record<string, string> = {
  reduce: '减仓',
  add: '增配',
  hold: '持有',
  watch: '观察',
}

const SIGNAL_TYPE_STYLES: Record<string, string> = {
  reduce: 'bg-rose-100 text-rose-800',
  add: 'bg-emerald-100 text-emerald-800',
  hold: 'bg-slate-100 text-slate-700',
  watch: 'bg-amber-100 text-amber-800',
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatScore(value: number) {
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

function StrengthStars({ strength }: { strength: number }) {
  const clamped = Math.min(5, Math.max(1, strength))

  return (
    <div className="flex items-center gap-0.5" aria-label={`强度 ${clamped} / 5`}>
      {Array.from({ length: 5 }, (_, index) => (
        <span
          key={index}
          className={index < clamped ? 'text-amber-400' : 'text-slate-200'}
          aria-hidden="true"
        >
          ★
        </span>
      ))}
    </div>
  )
}

function signalTitle(signal: Signal) {
  if (signal.fund_code) {
    return signal.fund_name ?? signal.fund_code
  }
  return signal.category_label ?? signal.category ?? '大类配置'
}

export default function SignalCard({ signal }: SignalCardProps) {
  const typeLabel = SIGNAL_TYPE_LABELS[signal.signal_type] ?? signal.signal_type
  const typeStyle = SIGNAL_TYPE_STYLES[signal.signal_type] ?? 'bg-slate-100 text-slate-700'
  const scoreTone =
    signal.score > 0 ? 'text-emerald-600' : signal.score < 0 ? 'text-rose-600' : 'text-slate-600'

  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${typeStyle}`}>
              {typeLabel}
            </span>
            <StrengthStars strength={signal.strength} />
          </div>
          <h3 className="mt-2 text-base font-semibold text-slate-900">{signalTitle(signal)}</h3>
          {signal.fund_code ? (
            <p className="mt-0.5 text-xs text-slate-500">{signal.fund_code}</p>
          ) : null}
        </div>
        <div className="text-right">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500">综合得分</p>
          <p className={`text-xl font-semibold ${scoreTone}`}>{formatScore(signal.score)}</p>
        </div>
      </div>

      {signal.suggested_amount !== 0 ? (
        <p className="mt-4 text-sm text-slate-700">
          建议金额：
          <span className="font-medium text-slate-900">
            {formatCurrency(Math.abs(signal.suggested_amount))}
          </span>
        </p>
      ) : null}

      {signal.reasons.length > 0 ? (
        <ul className="mt-4 space-y-2 border-t border-slate-100 pt-4">
          {signal.reasons.map((reason, index) => (
            <li key={`${reason.layer}-${reason.rule}-${index}`} className="text-sm text-slate-600">
              <span className="font-medium text-slate-700">{reason.rule}</span>
              <span className="text-slate-400"> · </span>
              {reason.detail}
            </li>
          ))}
        </ul>
      ) : null}
    </article>
  )
}
