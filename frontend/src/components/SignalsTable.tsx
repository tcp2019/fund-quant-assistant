import { Fragment, useMemo, useState } from 'react'
import {
  SIGNAL_TYPE_LABELS,
  SIGNAL_TYPE_STYLES,
  formatFundLabel,
  formatReasonRule,
  formatSignalAmount,
  formatSignalScore,
  resolveCorrelationPair,
  scoreTextClass,
  signalTitle,
  signalActionType,
  summarizeReasons,
} from '../utils/signalDisplay'
import type { Signal, SignalReason } from '../types'
import { fetchSignalInterpretation } from '../api/client'

interface SignalsTableProps {
  signals: Signal[]
}

type TypeFilter = 'all' | 'reduce' | 'add' | 'hold' | 'watch'

const FILTER_OPTIONS: { key: TypeFilter; label: string }[] = [
  { key: 'all', label: '全部' },
  { key: 'reduce', label: '减仓' },
  { key: 'add', label: '增配' },
  { key: 'hold', label: '持有' },
  { key: 'watch', label: '观察' },
]

function StrengthDots({ strength }: { strength: number }) {
  const clamped = Math.min(5, Math.max(1, strength))

  return (
    <div className="flex items-center gap-0.5" aria-label={`强度 ${clamped} / 5`}>
      {Array.from({ length: 5 }, (_, index) => (
        <span
          key={index}
          className={`inline-block h-1.5 w-1.5 rounded-full ${
            index < clamped ? 'bg-amber-400' : 'bg-slate-200'
          }`}
          aria-hidden="true"
        />
      ))}
    </div>
  )
}

function ReasonLine({ reason }: { reason: SignalReason }) {
  return (
    <li className="text-slate-600">
      <span className="font-medium text-slate-700">{formatReasonRule(reason.rule)}</span>
      <span className="text-slate-400"> · </span>
      {reason.detail}
    </li>
  )
}

function AIInterpretation({ signal }: { signal: Signal }) {
  const [state, setState] = useState<'idle' | 'loading' | 'result' | 'error'>(
    signal.interpretation ? 'result' : 'idle',
  )
  const [text, setText] = useState<string | null>(signal.interpretation ?? null)

  async function handleInterpret() {
    setState('loading')
    try {
      const result = await fetchSignalInterpretation(signal.id)
      if (result.interpretation) {
        setText(result.interpretation)
        setState('result')
      } else {
        setState('error')
      }
    } catch {
      setState('error')
    }
  }

  if (state === 'idle') {
    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation()
          handleInterpret()
        }}
        className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-indigo-600 transition-colors hover:bg-indigo-50"
      >
        <svg className="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
          <path
            fillRule="evenodd"
            d="M10 2a1 1 0 011 1v1.323l3.954 1.582 1.599-.8a1 1 0 01.894 1.79l-1.233.616 1.738 5.42a1 1 0 01-.285 1.05A3.989 3.989 0 0115 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.715-5.349L11 6.477V16h2a1 1 0 110 2H7a1 1 0 110-2h2V6.477L6.237 7.582l1.715 5.349a1 1 0 01-.285 1.05A3.989 3.989 0 015 15a3.989 3.989 0 01-2.667-1.019 1 1 0 01-.285-1.05l1.738-5.42-1.233-.616a1 1 0 01.894-1.79l1.599.8L9 4.323V3a1 1 0 011-1z"
            clipRule="evenodd"
          />
        </svg>
        AI 解读
      </button>
    )
  }

  if (state === 'loading') {
    return (
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-indigo-300" />
        AI 正在解读…
      </div>
    )
  }

  if (state === 'error') {
    return <p className="text-xs text-slate-400">AI 解读暂不可用</p>
  }

  return (
    <div className="rounded-lg border-l-2 border-indigo-300 bg-indigo-50/50 px-3 py-2.5 text-sm leading-relaxed text-slate-700">
      {text}
    </div>
  )
}


function SignalDetailPanel({
  signal,
  nameByCode,
}: {
  signal: Signal
  nameByCode: Record<string, string | null>
}) {
  const correlationReasons = signal.reasons.filter((reason) => reason.rule === 'high_correlation')
  const otherReasons = signal.reasons.filter((reason) => reason.rule !== 'high_correlation')

  return (
    <div className="space-y-4 bg-slate-50 px-5 py-4 text-sm">
      {otherReasons.length > 0 ? (
        <ul className="space-y-2">
          {otherReasons.map((reason, index) => (
            <ReasonLine key={`${reason.layer}-${reason.rule}-${index}`} reason={reason} />
          ))}
        </ul>
      ) : correlationReasons.length === 0 ? (
        <p className="text-slate-500">暂无详细原因</p>
      ) : null}

      {correlationReasons.length > 0 ? (
        <div className={otherReasons.length > 0 ? 'border-t border-slate-200 pt-4' : ''}>
          <h4 className="font-medium text-slate-900">
            高度相关持仓
            {signal.fund_code ? (
              <span className="ml-1 font-normal text-slate-500">
                · 以下基金与 {formatFundLabel(signal.fund_code, signal.fund_name)} 走势相近
              </span>
            ) : null}
          </h4>
          <ul className="mt-3 divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white">
            {correlationReasons.map((reason, index) => {
              const { pairedCode, pairedName, correlation } = resolveCorrelationPair(
                reason,
                signal.fund_code,
                nameByCode,
              )
              const pairedLabel = pairedCode
                ? formatFundLabel(pairedCode, pairedName)
                : reason.detail

              return (
                <li
                  key={`corr-${pairedCode ?? index}`}
                  className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-3 py-2"
                >
                  <p className="font-medium text-slate-900">{pairedLabel}</p>
                  {correlation != null && Number.isFinite(correlation) ? (
                    <p className="text-right tabular-nums text-slate-700">
                      相关系数{' '}
                      <span className="font-medium text-amber-700">
                        {correlation.toFixed(2)}
                      </span>
                    </p>
                  ) : null}
                </li>
              )
            })}
          </ul>
          <p className="mt-2 text-xs text-slate-500">
            近 90 日收益相关系数超过阈值，存在同源暴露，建议合并或减一只。
          </p>
        </div>
      ) : null}

      {!signal.fund_code && signal.signal_type === 'add' ? (
        <div className="border-t border-slate-200 pt-4">
          <h4 className="font-medium text-slate-900">参考候选（东方财富公开排行）</h4>
          {signal.candidates && signal.candidates.length > 0 ? (
            <ul className="mt-3 divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white">
              {signal.candidates.map((candidate) => (
                <li
                  key={candidate.fund_code}
                  className="flex items-start justify-between gap-3 px-3 py-2"
                >
                  <div>
                    <p className="font-medium text-slate-900">{candidate.fund_name}</p>
                    <p className="text-xs text-slate-500">{candidate.fund_code}</p>
                  </div>
                  {candidate.return_1m !== null && candidate.return_1m !== undefined ? (
                    <p className="text-right font-medium text-slate-900">
                      近1月 {candidate.return_1m.toFixed(2)}%
                    </p>
                  ) : candidate.return_1y !== null ? (
                    <p className="text-right font-medium text-slate-900">
                      近1年 {candidate.return_1y.toFixed(2)}%
                    </p>
                  ) : null}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 text-slate-500">
              无法获取可靠排行数据，请稍后重试或在设置页同步数据后刷新。
            </p>
          )}
          <p className="mt-2 text-xs text-slate-500">
            按近 1 月收益排序（无则近 1 年），仅供参考，不构成投资建议。
          </p>
        </div>
      ) : null}

      {signal.fund_code ? (
        <div className="border-t border-slate-200 pt-4">
          <AIInterpretation signal={signal} />
        </div>
      ) : null}
    </div>
  )
}

export default function SignalsTable({ signals }: SignalsTableProps) {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const nameByCode = useMemo(() => {
    const map: Record<string, string | null> = {}
    for (const signal of signals) {
      if (signal.fund_code) {
        map[signal.fund_code] = signal.fund_name
      }
    }
    return map
  }, [signals])

  const counts = useMemo(() => {
    const result: Record<TypeFilter, number> = {
      all: signals.length,
      reduce: 0,
      add: 0,
      hold: 0,
      watch: 0,
    }
    for (const signal of signals) {
      const action = signalActionType(signal)
      if (action in result) {
        result[action as Exclude<TypeFilter, 'all'>] += 1
      }
    }
    return result
  }, [signals])

  const filteredSignals = useMemo(() => {
    if (typeFilter === 'all') return signals
    return signals.filter((signal) => signalActionType(signal) === typeFilter)
  }, [signals, typeFilter])

  function toggleExpanded(id: number) {
    setExpandedId((current) => (current === id ? null : id))
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 px-5 py-3">
        {FILTER_OPTIONS.map((option) => {
          const active = typeFilter === option.key
          return (
            <button
              key={option.key}
              type="button"
              onClick={() => {
                setTypeFilter(option.key)
                setExpandedId(null)
              }}
              className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                active
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {option.label}
              <span className={active ? 'text-slate-300' : 'text-slate-400'}>
                {' '}
                {counts[option.key]}
              </span>
            </button>
          )
        })}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="w-8 px-3 py-2.5 font-medium" aria-label="展开" />
              <th className="px-3 py-2.5 font-medium">类型</th>
              <th className="px-3 py-2.5 font-medium">标的</th>
              <th className="px-3 py-2.5 font-medium text-center">强度</th>
              <th className="px-3 py-2.5 font-medium text-right">得分</th>
              <th className="px-3 py-2.5 font-medium text-right">建议金额</th>
              <th className="hidden px-3 py-2.5 font-medium lg:table-cell">原因摘要</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredSignals.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                  该分类下暂无信号
                </td>
              </tr>
            ) : (
              filteredSignals.map((signal) => {
                const actionType = signalActionType(signal)
                const typeLabel = SIGNAL_TYPE_LABELS[actionType] ?? actionType
                const typeStyle = SIGNAL_TYPE_STYLES[actionType] ?? 'bg-slate-100 text-slate-700'
                const expanded = expandedId === signal.id

                return (
                  <Fragment key={signal.id}>
                    <tr
                      className={`cursor-pointer text-slate-700 transition-colors hover:bg-slate-50 ${
                        expanded ? 'bg-slate-50' : ''
                      }`}
                      onClick={() => toggleExpanded(signal.id)}
                    >
                      <td className="px-3 py-2 text-center text-slate-400">
                        <span
                          className={`inline-block transition-transform ${expanded ? 'rotate-90' : ''}`}
                          aria-hidden="true"
                        >
                          ›
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <span
                          className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${typeStyle}`}
                        >
                          {typeLabel}
                        </span>
                      </td>
                      <td className="max-w-[220px] px-3 py-2">
                        <div className="truncate font-medium text-slate-900">
                          {signalTitle(signal)}
                        </div>
                        {signal.fund_code ? (
                          <div className="text-xs text-slate-500">{signal.fund_code}</div>
                        ) : signal.category_label ? (
                          <div className="text-xs text-slate-500">{signal.category_label}</div>
                        ) : null}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-center">
                          <StrengthDots strength={signal.strength} />
                        </div>
                      </td>
                      <td
                        className={`px-3 py-2 text-right font-medium tabular-nums ${scoreTextClass(signal.score)}`}
                      >
                        {formatSignalScore(signal.score)}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-900">
                        {signal.suggested_amount !== 0
                          ? formatSignalAmount(signal.suggested_amount)
                          : '—'}
                      </td>
                      <td className="hidden max-w-xs truncate px-3 py-2 text-slate-500 lg:table-cell">
                        {summarizeReasons(signal)}
                      </td>
                    </tr>
                    {expanded ? (
                      <tr>
                        <td colSpan={7} className="p-0">
                          <SignalDetailPanel signal={signal} nameByCode={nameByCode} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="border-t border-slate-100 px-5 py-2 text-xs text-slate-500">
        显示 {filteredSignals.length} / {signals.length} 条 · 点击行展开详情
      </div>
    </div>
  )
}
