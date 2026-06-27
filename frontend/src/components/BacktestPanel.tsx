import { useMutation, useQueryClient } from '@tanstack/react-query'
import type { SensitivityReport, SnapshotStatsOut } from '../types'
import { runBacktest } from '../api/client'
import { queryKeys } from '../api/queries'

const CATEGORY_LABELS: Record<string, string> = {
  stock: '股票型',
  bond: '债券型',
  money: '货币/理财',
  qdii: 'QDII/海外',
  gold: '黄金',
  other: '其他',
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(value)
}

function formatSnapshotDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function BacktestPanel({
  sensitivity,
  snapshotStats,
}: {
  sensitivity: SensitivityReport | null
  snapshotStats: SnapshotStatsOut | null
}) {
  const queryClient = useQueryClient()
  const backtestMutation = useMutation({
    mutationFn: runBacktest,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.backtestSensitivity })
      queryClient.invalidateQueries({ queryKey: queryKeys.backtestSnapshotStats })
    },
  })

  const currentThreshold =
    sensitivity?.scenarios.find((s) => s.triggered_categories > 0)?.threshold_pct ?? 5

  return (
    <div className="space-y-6">
      <section>
        <div className="flex items-center gap-3 mb-4">
          <button
            type="button"
            onClick={() => backtestMutation.mutate()}
            disabled={backtestMutation.isPending}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {backtestMutation.isPending ? '回测中...' : '运行历史回测'}
          </button>
        </div>

        {backtestMutation.isError ? (
          <p className="mt-3 text-sm text-rose-600">
            回测请求失败：{backtestMutation.error instanceof Error ? backtestMutation.error.message : '未知错误'}
          </p>
        ) : null}

        {backtestMutation.isSuccess && backtestMutation.data ? (
          <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <h4 className="font-medium text-slate-900">回测结果</h4>
            <div className="mt-2 grid gap-2 text-sm sm:grid-cols-3">
              <div>
                <span className="text-slate-500">测试快照数：</span>
                <span className="font-mono text-slate-900">{backtestMutation.data.snapshots_tested}</span>
              </div>
              <div>
                <span className="text-slate-500">生成信号数：</span>
                <span className="font-mono text-slate-900">{backtestMutation.data.signals_generated}</span>
              </div>
              <div>
                <span className="text-slate-500">命中率：</span>
                <span className="font-mono text-slate-900">
                  {backtestMutation.data.hit_rate !== null
                    ? `${(backtestMutation.data.hit_rate * 100).toFixed(1)}%`
                    : '—'}
                </span>
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-500">{backtestMutation.data.detail}</p>
          </div>
        ) : null}
      </section>

      <section>
        <h3 className="text-lg font-medium text-slate-900">再平衡带宽敏感性</h3>
        <p className="mt-1 text-sm text-slate-500">
          基于当前持仓与策略目标，模拟不同偏差阈值下会触发的大类调整（只读回放，不写入信号）
        </p>
        {!sensitivity?.scenarios.length ? (
          <p className="mt-4 text-sm text-slate-500">暂无数据</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">偏差阈值</th>
                  <th className="px-3 py-2 font-medium">触发大类数</th>
                  <th className="px-3 py-2 font-medium">详情</th>
                </tr>
              </thead>
              <tbody>
                {sensitivity.scenarios.map((scenario) => (
                  <tr key={scenario.threshold_pct} className="border-b border-slate-100">
                    <td className="px-3 py-2 font-mono tabular-nums text-slate-900">
                      ±{scenario.threshold_pct}%
                    </td>
                    <td className="px-3 py-2 tabular-nums text-slate-900">
                      {scenario.triggered_categories}
                    </td>
                    <td className="px-3 py-2 text-slate-600">
                      {scenario.signals.length === 0 ? (
                        '—'
                      ) : (
                        <ul className="space-y-1">
                          {scenario.signals.map((signal) => (
                            <li key={`${scenario.threshold_pct}-${signal.category}`}>
                              {CATEGORY_LABELS[signal.category] ?? signal.category}
                              {' · '}
                              {signal.signal_type === 'add' ? '低配' : '超配'}{' '}
                              {Math.abs(signal.deviation_pct).toFixed(1)}%
                              {' · '}
                              {formatMoney(Math.abs(signal.suggested_amount))}
                            </li>
                          ))}
                        </ul>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {sensitivity.total_value > 0 ? (
              <p className="mt-3 text-xs text-slate-500">
                组合总市值 {formatMoney(sensitivity.total_value)} · 当前 Settings 默认带宽 5%
                {currentThreshold !== 5 ? ` · 本表最低触发约 ±${currentThreshold}%` : ''}
              </p>
            ) : null}
          </div>
        )}
      </section>

      <section>
        <h3 className="text-lg font-medium text-slate-900">快照历史再平衡触发</h3>
        <p className="mt-1 text-sm text-slate-500">
          各历史快照在当前策略目标与带宽下的再平衡触发次数；大类最多持仓只数反映分散度
        </p>
        {!snapshotStats?.snapshots.length ? (
          <p className="mt-4 text-sm text-slate-500">暂无历史快照</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">快照</th>
                  <th className="px-3 py-2 font-medium">时间</th>
                  <th className="px-3 py-2 font-medium">触发大类</th>
                  <th className="px-3 py-2 font-medium">单类最多持仓</th>
                </tr>
              </thead>
              <tbody>
                {snapshotStats.snapshots.map((row) => (
                  <tr key={row.snapshot_id} className="border-b border-slate-100">
                    <td className="px-3 py-2 font-mono text-slate-900">#{row.snapshot_id}</td>
                    <td className="px-3 py-2 text-slate-600">{formatSnapshotDate(row.created_at)}</td>
                    <td className="px-3 py-2 tabular-nums text-slate-900">
                      {row.rebalance_triggers}
                    </td>
                    <td className="px-3 py-2 tabular-nums text-slate-900">
                      {row.category_count_max} 只
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
