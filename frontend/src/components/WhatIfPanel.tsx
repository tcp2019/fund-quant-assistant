import { useState } from 'react'
import type { Overview } from '../types'

interface WhatIfPanelProps {
  overview: Overview | null
}

export default function WhatIfPanel({ overview }: WhatIfPanelProps) {
  const [sellFund, setSellFund] = useState('')
  const [buyFund, setBuyFund] = useState('')
  const [amount, setAmount] = useState(1000)

  if (!overview || overview.holdings.length === 0) {
    return (
      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">模拟调仓</h3>
        <p className="mt-2 text-sm text-slate-500">导入持仓后可模拟调仓影响</p>
      </section>
    )
  }

  const holdings = overview.holdings
  const totalValue = overview.total_value
  const sellHolding = holdings.find(h => h.fund_code === sellFund)
  const buyHolding = holdings.find(h => h.fund_code === buyFund)

  // Compute before/after
  const currentAlloc: Record<string, number> = {}
  holdings.forEach(h => {
    currentAlloc[h.fund_code] = (h.market_value / totalValue) * 100
  })

  const afterAlloc = { ...currentAlloc }
  if (sellHolding && amount > 0) {
    afterAlloc[sellFund] = ((sellHolding.market_value - amount) / totalValue) * 100
  }
  if (buyHolding && amount > 0) {
    afterAlloc[buyFund] = ((buyHolding.market_value + amount) / totalValue) * 100
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h3 className="text-lg font-medium text-slate-900">模拟调仓</h3>
      <p className="mt-1 text-sm text-slate-500">选择买卖基金和金额，预览组合指标变化（仅前端计算，不写入持仓）</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">卖出基金</label>
          <select
            value={sellFund}
            onChange={e => setSellFund(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">-- 选择基金 --</option>
            {holdings.map(h => (
              <option key={h.fund_code} value={h.fund_code}>{h.fund_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">买入基金</label>
          <select
            value={buyFund}
            onChange={e => setBuyFund(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">-- 选择基金 --</option>
            {holdings.map(h => (
              <option key={h.fund_code} value={h.fund_code}>{h.fund_name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">调仓金额</label>
          <input
            type="number"
            value={amount}
            onChange={e => setAmount(Number(e.target.value))}
            min={100}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
        </div>
      </div>

      {sellHolding && buyHolding && amount > 0 && (
        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <div className="rounded-lg border border-slate-200 p-3">
            <h4 className="text-sm font-medium text-slate-700">调仓前</h4>
            <p className="text-xs text-slate-500 mt-1">
              {sellHolding.fund_name}: {currentAlloc[sellFund]?.toFixed(1)}%
            </p>
            <p className="text-xs text-slate-500">
              {buyHolding.fund_name}: {currentAlloc[buyFund]?.toFixed(1)}%
            </p>
          </div>
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-3">
            <h4 className="text-sm font-medium text-indigo-700">调仓后</h4>
            <p className="text-xs text-indigo-600 mt-1">
              {sellHolding.fund_name}: {afterAlloc[sellFund]?.toFixed(1)}% ↓
            </p>
            <p className="text-xs text-indigo-600">
              {buyHolding.fund_name}: {afterAlloc[buyFund]?.toFixed(1)}% ↑
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
