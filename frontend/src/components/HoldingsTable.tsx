import type { Holding } from '../types'
import { formatCurrency, formatProfitAmount, formatSignedPercent } from '../utils/format'
import { profitLossTextClass } from '../utils/profitLoss'
import ThemeTags from './ThemeTags'

interface HoldingsTableProps {
  holdings: Holding[]
}

export default function HoldingsTable({ holdings }: HoldingsTableProps) {
  const sortedHoldings = [...holdings].sort((a, b) => b.weight_pct - a.weight_pct)
  const hasRealtime = sortedHoldings.some(
    (h) => h.current_value && h.current_value > 0 && h.nav_date,
  )

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 px-5 py-4">
        <h2 className="text-base font-semibold text-slate-900">持仓明细</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="px-5 py-3 font-medium">基金</th>
              <th className="px-5 py-3 font-medium">平台</th>
              <th className="px-5 py-3 font-medium text-right">权重</th>
              <th className="px-5 py-3 font-medium text-right">
                {hasRealtime ? '实时市值' : '市值'}
              </th>
              <th className="px-5 py-3 font-medium text-right">成本价</th>
              <th className="px-5 py-3 font-medium text-right">盈亏</th>
              <th className="px-5 py-3 font-medium text-right">收益率</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {sortedHoldings.map((holding) => {
              const displayValue =
                hasRealtime && holding.current_value ? holding.current_value : holding.market_value
              const displayProfit =
                hasRealtime && holding.current_profit !== undefined
                  ? holding.current_profit
                  : holding.profit
              const displayProfitRate =
                hasRealtime && holding.current_value && holding.current_value > 0
                  ? displayProfit / (displayValue - displayProfit)
                  : holding.profit_rate

              return (
                <tr
                  key={`${holding.fund_code}-${holding.platform}`}
                  className="text-slate-700"
                >
                  <td className="px-5 py-3">
                    <div className="font-medium text-slate-900">{holding.fund_name}</div>
                    <div className="text-xs text-slate-500">{holding.fund_code}</div>
                    <ThemeTags themes={holding.themes ?? []} />
                  </td>
                  <td className="px-5 py-3 capitalize">{holding.platform}</td>
                  <td className="px-5 py-3 text-right">{holding.weight_pct.toFixed(2)}%</td>
                  <td className="px-5 py-3 text-right">
                    {hasRealtime && holding.current_value ? (
                      <div>
                        <div>{formatCurrency(holding.current_value)}</div>
                        <div className="text-xs text-slate-400">
                          导入 {formatCurrency(holding.market_value)}
                        </div>
                      </div>
                    ) : (
                      formatCurrency(holding.market_value)
                    )}
                  </td>
                  <td className="px-5 py-3 text-right">{formatCurrency(holding.cost_price)}</td>
                  <td
                    className={`px-5 py-3 text-right font-medium ${profitLossTextClass(displayProfit)}`}
                  >
                    {formatProfitAmount(displayProfit)}
                  </td>
                  <td
                    className={`px-5 py-3 text-right ${profitLossTextClass(displayProfitRate)}`}
                  >
                    {formatSignedPercent(displayProfitRate)}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
