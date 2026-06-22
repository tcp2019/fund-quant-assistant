import { Fragment, useState } from 'react'
import type { ActionItem, FundCandidate } from '../types'
import {
  formatSignalAmount,
  formatSignalScore,
  scoreTextClass,
} from '../utils/signalDisplay'

interface ActionListProps {
  title: string
  items: ActionItem[]
  emptyText: string
  tone: 'sell' | 'buy' | 'explore'
}

const TONE_STYLES = {
  sell: {
    header: 'border-rose-200 bg-rose-50/60',
    badge: 'bg-rose-100 text-rose-800',
  },
  buy: {
    header: 'border-emerald-200 bg-emerald-50/60',
    badge: 'bg-emerald-100 text-emerald-800',
  },
  explore: {
    header: 'border-sky-200 bg-sky-50/60',
    badge: 'bg-sky-100 text-sky-800',
  },
}

function actionTitle(item: ActionItem) {
  if (item.fund_code) {
    return item.fund_name ?? item.fund_code
  }
  return item.category_label ?? item.category ?? '大类配置'
}

function formatCandidateReturn(candidate: FundCandidate) {
  if (candidate.return_1m !== null && candidate.return_1m !== undefined) {
    return `近1月 ${candidate.return_1m.toFixed(2)}%`
  }
  if (candidate.return_1y !== null && candidate.return_1y !== undefined) {
    return `近1年 ${candidate.return_1y.toFixed(2)}%`
  }
  return '—'
}

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

function ActionDetailPanel({ item }: { item: ActionItem }) {
  return (
    <div className="space-y-4 bg-slate-50 px-5 py-4 text-sm">
      <p className="text-slate-600">{item.reason_summary || '—'}</p>

      {item.candidates.length > 0 ? (
        <div className="border-t border-slate-200 pt-4">
          <h4 className="font-medium text-slate-900">参考候选（东方财富公开排行）</h4>
          <ul className="mt-3 divide-y divide-slate-200 overflow-hidden rounded-lg border border-slate-200 bg-white">
            {item.candidates.map((candidate) => (
              <li
                key={candidate.fund_code}
                className="flex items-start justify-between gap-3 px-3 py-2"
              >
                <div>
                  <p className="font-medium text-slate-900">{candidate.fund_name}</p>
                  <p className="text-xs text-slate-500">{candidate.fund_code}</p>
                </div>
                <p className="text-right font-medium tabular-nums text-slate-900">
                  {formatCandidateReturn(candidate)}
                </p>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-slate-500">
            按近 1 月收益排序（无则近 1 年），仅供参考，不构成投资建议。
          </p>
        </div>
      ) : null}
    </div>
  )
}

export default function ActionList({ title, items, emptyText, tone }: ActionListProps) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const styles = TONE_STYLES[tone]

  function itemKey(item: ActionItem, index: number) {
    return `${item.action}-${item.signal_id ?? item.fund_code ?? item.category ?? index}`
  }

  function toggleExpanded(key: string) {
    setExpandedKey((current) => (current === key ? null : key))
  }

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className={`border-b px-5 py-3 ${styles.header}`}>
        <h3 className="font-semibold text-slate-900">{title}</h3>
      </div>

      {items.length === 0 ? (
        <p className="px-5 py-6 text-sm text-slate-500">{emptyText}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="w-8 px-3 py-2.5 font-medium" aria-label="展开" />
                <th className="px-3 py-2.5 font-medium">标的</th>
                <th className="px-3 py-2.5 font-medium text-center">强度</th>
                <th className="px-3 py-2.5 font-medium text-right">得分</th>
                <th className="px-3 py-2.5 font-medium text-right">建议金额</th>
                <th className="hidden px-3 py-2.5 font-medium lg:table-cell">原因摘要</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {items.map((item, index) => {
                const key = itemKey(item, index)
                const expanded = expandedKey === key

                return (
                  <Fragment key={key}>
                    <tr
                      className={`cursor-pointer text-slate-700 transition-colors hover:bg-slate-50 ${
                        expanded ? 'bg-slate-50' : ''
                      }`}
                      onClick={() => toggleExpanded(key)}
                    >
                      <td className="px-3 py-2 text-center text-slate-400">
                        <span
                          className={`inline-block transition-transform ${expanded ? 'rotate-90' : ''}`}
                          aria-hidden="true"
                        >
                          ›
                        </span>
                      </td>
                      <td className="max-w-[220px] px-3 py-2">
                        <div className="truncate font-medium text-slate-900">
                          {actionTitle(item)}
                        </div>
                        {item.fund_code ? (
                          <div className="text-xs text-slate-500">{item.fund_code}</div>
                        ) : item.category_label ? (
                          <div className="text-xs text-slate-500">{item.category_label}</div>
                        ) : null}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-center">
                          <StrengthDots strength={item.strength} />
                        </div>
                      </td>
                      <td
                        className={`px-3 py-2 text-right font-medium tabular-nums ${scoreTextClass(item.score)}`}
                      >
                        {formatSignalScore(item.score)}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-slate-900">
                        {item.suggested_amount !== 0
                          ? formatSignalAmount(item.suggested_amount)
                          : '—'}
                      </td>
                      <td className="hidden max-w-xs truncate px-3 py-2 text-slate-500 lg:table-cell">
                        {item.reason_summary || '—'}
                      </td>
                    </tr>
                    {expanded ? (
                      <tr>
                        <td colSpan={6} className="p-0">
                          <ActionDetailPanel item={item} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
