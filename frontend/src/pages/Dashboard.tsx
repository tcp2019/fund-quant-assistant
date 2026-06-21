import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import HoldingsTable from '../components/HoldingsTable'
import StatCard from '../components/StatCard'
import type { Overview } from '../types'

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

export default function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function loadOverview() {
      try {
        const data = await api.get<Overview>('/api/portfolio/overview')
        if (!cancelled) {
          setOverview(data)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载失败')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void loadOverview()

    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载组合概览：{error}
      </div>
    )
  }

  if (!overview || overview.holdings.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h2 className="text-xl font-semibold text-slate-900">还没有持仓数据</h2>
        <p className="mt-2 text-slate-500">
          通过 OCR 导入或手动录入第一笔持仓，即可在这里查看总览。
        </p>
        <Link
          to="/import"
          className="mt-6 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          去导入持仓
        </Link>
      </div>
    )
  }

  const profitTone =
    overview.total_profit > 0 ? 'profit' : overview.total_profit < 0 ? 'loss' : 'default'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">组合总览</h2>
        <p className="mt-1 text-sm text-slate-500">
          快照 #{overview.snapshot_id ?? '—'} · 共 {overview.holdings.length} 只基金
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="总市值" value={formatCurrency(overview.total_value)} />
        <StatCard title="总成本" value={formatCurrency(overview.total_cost)} />
        <StatCard
          title="总盈亏"
          value={formatCurrency(overview.total_profit)}
          subtitle={formatPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
        <StatCard
          title="收益率"
          value={formatPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
      </div>

      <HoldingsTable holdings={overview.holdings} />
    </div>
  )
}
