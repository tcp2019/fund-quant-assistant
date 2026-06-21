import type { Holding } from '../types'

interface HoldingsTableProps {
  holdings: Holding[]
}

function formatCurrency(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 2,
  }).format(value)
}

function formatPercent(value: number) {
  return `${(value * 100).toFixed(2)}%`
}

export default function HoldingsTable({ holdings }: HoldingsTableProps) {
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
              <th className="px-5 py-3 font-medium text-right">市值</th>
              <th className="px-5 py-3 font-medium text-right">成本价</th>
              <th className="px-5 py-3 font-medium text-right">盈亏</th>
              <th className="px-5 py-3 font-medium text-right">收益率</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {holdings.map((holding) => (
              <tr key={`${holding.fund_code}-${holding.platform}`} className="text-slate-700">
                <td className="px-5 py-3">
                  <div className="font-medium text-slate-900">{holding.fund_name}</div>
                  <div className="text-xs text-slate-500">{holding.fund_code}</div>
                </td>
                <td className="px-5 py-3 capitalize">{holding.platform}</td>
                <td className="px-5 py-3 text-right">{holding.weight_pct.toFixed(2)}%</td>
                <td className="px-5 py-3 text-right">{formatCurrency(holding.market_value)}</td>
                <td className="px-5 py-3 text-right">{formatCurrency(holding.cost_price)}</td>
                <td
                  className={`px-5 py-3 text-right font-medium ${
                    holding.profit >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {formatCurrency(holding.profit)}
                </td>
                <td
                  className={`px-5 py-3 text-right ${
                    holding.profit_rate >= 0 ? 'text-emerald-600' : 'text-rose-600'
                  }`}
                >
                  {formatPercent(holding.profit_rate)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
