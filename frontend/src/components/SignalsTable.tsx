import { Fragment, useMemo, useState } from 'react'
import type { Signal } from '../types'
import {
  SIGNAL_TYPE_LABELS,
  SIGNAL_TYPE_STYLES,
  formatReasonRule,
  formatSignalAmount,
  formatSignalScore,
  scoreTextClass,
  signalTitle,
  signalActionType,
  summarizeReasons,
} from '../utils/signalDisplay'

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

function SignalDetailPanel({ signal }: { signal: Signal }) {
  return (
    <div className="space-y-4 bg-slate-50 px-5 py-4 text-sm">
      {signal.reasons.length > 0 ? (
        <ul className="space-y-2">
          {signal.reasons.map((reason, index) => (
            <li key={`${reason.layer}-${reason.rule}-${index}`} className="text-slate-600">
              <span className="font-medium text-slate-700">{formatReasonRule(reason.rule)}</span>
              <span className="text-slate-400"> · </span>
              {reason.detail}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-slate-500">暂无详细原因</p>
      )}

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
    </div>
  )
}

export default function SignalsTable({ signals }: SignalsTableProps) {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all')
  const [expandedId, setExpandedId] = useState<number | null>(null)

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
                          <SignalDetailPanel signal={signal} />
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
