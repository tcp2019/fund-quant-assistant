import type { SensitivityReport, SnapshotStatsOut } from '../types'

const CATEGORY_LABELS: Record<string, string> = {
  stock: '股票型',
  bond: '债券型',
  money: '货币/理财',
  qdii: 'QDII/海外',
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
  const currentThreshold =
    sensitivity?.scenarios.find((s) => s.triggered_categories > 0)?.threshold_pct ?? 5

  return (
    <div className="space-y-6">
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
