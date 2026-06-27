import { Link } from 'react-router-dom'
import { useHoldings, useSnapshots } from '../api/hooks'
import HoldingsTable from '../components/HoldingsTable'
import { profitLossToneClass } from '../utils/profitLoss'

function formatCurrency(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 2,
  }).format(value)
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function sourceLabel(source: string) {
  if (source === 'ocr') return 'OCR 导入'
  if (source === 'manual') return '手动录入'
  return source
}

function formatValueChange(current: number, previous: number | null) {
  if (previous === null) {
    return { text: '—', tone: 'default' as const }
  }
  const delta = current - previous
  if (delta === 0) {
    return { text: '±¥0.00', tone: 'default' as const }
  }
  const sign = delta > 0 ? '+' : ''
  return {
    text: `${sign}${formatCurrency(delta)}`,
    tone: delta > 0 ? ('profit' as const) : ('loss' as const),
  }
}

export default function HoldingsPage() {
  const { data: overview, isLoading, error } = useHoldings()
  const { data: snapshotsData } = useSnapshots()

  const snapshots = snapshotsData?.snapshots ?? []

  if (isLoading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载持仓数据：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  if (!overview || overview.holdings.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h2 className="text-xl font-semibold text-slate-900">还没有持仓数据</h2>
        <p className="mt-2 text-slate-500">导入或录入持仓后，可在此查看明细与快照历史。</p>
        <Link
          to="/import"
          className="mt-6 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          去导入持仓
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">持仓明细</h2>
        <p className="mt-1 text-sm text-slate-500">
          当前快照 #{overview.snapshot_id ?? '—'} · 总市值{' '}
          {formatCurrency(overview.total_value)}
        </p>
      </div>

      <HoldingsTable holdings={overview.holdings} />

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-base font-semibold text-slate-900">快照历史</h2>
          <p className="mt-1 text-sm text-slate-500">
            每次 OCR 确认或手动编辑产生一条快照，「较上一版」为与更早快照的总市值差值。
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-5 py-3 font-medium">快照</th>
                <th className="px-5 py-3 font-medium">时间</th>
                <th className="px-5 py-3 font-medium">来源</th>
                <th className="px-5 py-3 font-medium text-right">总市值</th>
                <th className="px-5 py-3 font-medium text-right">较上一版</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {snapshots.map((snapshot, index) => {
                const previous =
                  index < snapshots.length - 1 ? snapshots[index + 1].total_value : null
                const change = formatValueChange(snapshot.total_value, previous)
                const isCurrent = snapshot.id === overview.snapshot_id

                return (
                  <tr
                    key={snapshot.id}
                    className={`text-slate-700 ${isCurrent ? 'bg-slate-50/80' : ''}`}
                  >
                    <td className="px-5 py-3">
                      <div className="font-medium text-slate-900">#{snapshot.id}</div>
                      {isCurrent && (
                        <div className="text-xs font-medium text-sky-600">当前</div>
                      )}
                    </td>
                    <td className="px-5 py-3">{formatDateTime(snapshot.created_at)}</td>
                    <td className="px-5 py-3">{sourceLabel(snapshot.source)}</td>
                    <td className="px-5 py-3 text-right font-medium">
                      {formatCurrency(snapshot.total_value)}
                    </td>
                    <td
                      className={`px-5 py-3 text-right font-medium ${profitLossToneClass(
                        change.tone,
                        'text-slate-500',
                      )}`}
                    >
                      {change.text}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
