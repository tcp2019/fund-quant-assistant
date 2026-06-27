import type { StructuralAction } from '../types'

interface StructuralAlertsProps {
  items: StructuralAction[]
  className?: string
}

const ACTION_META: Record<
  StructuralAction['action'],
  { emoji: string; title: string }
> = {
  consolidate: { emoji: '📦', title: '基金太多，建议整理' },
  rebalance_review: { emoji: '📋', title: '该整体看一眼了' },
}

function blockedBuyText(item: StructuralAction) {
  if (item.action !== 'consolidate' || !item.blocked_buy_count) {
    return null
  }
  return `已暂停 ${item.blocked_buy_count} 笔类内增配`
}

export default function StructuralAlerts({ items, className = '' }: StructuralAlertsProps) {
  if (items.length === 0) {
    return null
  }

  return (
    <section className={`space-y-3 ${className}`.trim()}>
      <div>
        <h3 className="text-base font-semibold text-slate-900">先处理这些</h3>
        <p className="mt-1 text-sm text-slate-500">整理完组合结构后，再考虑下方的买卖建议</p>
      </div>
      <ul className="space-y-3">
        {items.map((item) => {
          const meta = ACTION_META[item.action]
          const blockedText = blockedBuyText(item)
          return (
            <li
              key={`${item.action}-${item.category}`}
              className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
            >
              <p className="font-medium">
                <span aria-hidden="true">{meta.emoji} </span>
                {meta.title} · {item.category_label}
                {item.fund_count ? `（${item.fund_count} 只）` : ''}
              </p>
              <p className="mt-1 text-amber-900">{item.detail}</p>
              {blockedText ? <p className="mt-1 text-xs text-amber-800">{blockedText}</p> : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
