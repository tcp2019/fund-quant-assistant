import type { Holding } from '../types'
import { chartColor } from '../utils/chartColors'
import { formatCurrency } from '../utils/format'

interface ConcentrationCardProps {
  topHoldings: Holding[]
  concentrationTop5Pct: number
}

export default function ConcentrationCard({
  topHoldings,
  concentrationTop5Pct,
}: ConcentrationCardProps) {
  if (topHoldings.length === 0) {
    return <p className="text-sm text-slate-500">暂无集中度数据</p>
  }

  const maxWeight = topHoldings[0]?.weight_pct ?? 100

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-indigo-100 bg-gradient-to-br from-indigo-50 to-sky-50 px-4 py-3">
        <p className="text-xs font-medium text-indigo-600">Top5 合计占比</p>
        <p className="mt-1 text-2xl font-semibold tabular-nums text-indigo-950">
          {concentrationTop5Pct.toFixed(2)}%
        </p>
      </div>

      <ul className="space-y-3">
        {topHoldings.map((holding, index) => (
          <li key={`${holding.fund_code}-${holding.platform}`}>
            <div className="flex items-start justify-between gap-3 text-sm">
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-slate-900">{holding.fund_name}</p>
                <p className="text-xs text-slate-500">{holding.fund_code || '未识别代码'}</p>
              </div>
              <div className="text-right">
                <p className="font-semibold tabular-nums text-slate-900">
                  {holding.weight_pct.toFixed(2)}%
                </p>
                <p className="text-xs text-slate-500">{formatCurrency(holding.market_value)}</p>
              </div>
            </div>
            <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${(holding.weight_pct / maxWeight) * 100}%`,
                  backgroundColor: chartColor(index),
                }}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
