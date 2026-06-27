import { Link } from 'react-router-dom'
import type { ActionItem, OpportunitiesOut } from '../types'
import { formatSignalAmount } from '../utils/signalDisplay'

interface AdviceSummaryProps {
  data: OpportunitiesOut | null
}

function actionTitle(item: ActionItem) {
  if (item.fund_code) {
    return item.fund_name ?? item.fund_code
  }
  return item.category_label ?? item.category ?? '大类配置'
}

export default function AdviceSummary({ data }: AdviceSummaryProps) {
  if (!data || data.snapshot_id === null) {
    return null
  }

  const structural = data.structural_actions?.[0]
  const sell = data.sell_actions[0]
  const buy = data.buy_actions[0]
  const hasAny = structural || sell || buy

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-slate-900">本周建议摘要</h3>
          <p className="mt-1 text-sm text-slate-500">
            {hasAny ? '优先处理下列事项，详情见「本周建议」' : '当前暂无明确调整建议'}
          </p>
        </div>
        <Link
          to="/advice"
          className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
        >
          查看全部 →
        </Link>
      </div>

      {hasAny ? (
        <ul className="mt-4 space-y-2 text-sm">
          {structural ? (
            <li className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-950">
              <span className="font-medium">先处理：</span>
              {structural.detail}
            </li>
          ) : null}
          {sell ? (
            <li className="flex items-start justify-between gap-3 rounded-lg bg-rose-50/80 px-3 py-2">
              <span>
                <span className="font-medium text-rose-900">建议减仓 </span>
                {actionTitle(sell)}
              </span>
              {sell.suggested_amount !== 0 ? (
                <span className="shrink-0 tabular-nums text-rose-800">
                  {formatSignalAmount(sell.suggested_amount)}
                </span>
              ) : null}
            </li>
          ) : null}
          {buy ? (
            <li className="flex items-start justify-between gap-3 rounded-lg bg-emerald-50/80 px-3 py-2">
              <span>
                <span className="font-medium text-emerald-900">建议加仓 </span>
                {actionTitle(buy)}
              </span>
              {buy.suggested_amount !== 0 ? (
                <span className="shrink-0 tabular-nums text-emerald-800">
                  {formatSignalAmount(buy.suggested_amount)}
                </span>
              ) : null}
            </li>
          ) : null}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-500">组合整体较为均衡，保持观察即可。</p>
      )}
    </section>
  )
}
