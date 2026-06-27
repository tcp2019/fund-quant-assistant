import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useOpportunities, useSignals, useSyncData } from '../api/hooks'
import ActionList from '../components/ActionList'
import SignalsTable from '../components/SignalsTable'
import StructuralAlerts from '../components/StructuralAlerts'
import type { Signal } from '../types'
import { maybeNotifyStrongSignals, summarizeStrongSignals } from '../utils/notifications'

function sortSignals(signals: Signal[]) {
  return [...signals].sort((a, b) => b.score - a.score)
}

export default function AdvicePage() {
  const [searchParams] = useSearchParams()
  const expandAll = searchParams.get('tab') === 'all'
  const [detailsOpen, setDetailsOpen] = useState(expandAll)
  const signalsEnabled = detailsOpen || expandAll

  const { data, isLoading, error, refetch } = useOpportunities({
    sell_limit: 10,
    buy_limit: 10,
    explore_limit: 10,
    include_hot_themes: false,
  })
  const {
    data: signalsData,
    isLoading: signalsLoading,
    error: signalsError,
    refetch: refetchSignals,
  } = useSignals({ enabled: signalsEnabled })
  const syncMutation = useSyncData()

  const signals = signalsData?.signals ? sortSignals(signalsData.signals) : []
  const snapshotId = data?.snapshot_id ?? signalsData?.snapshot_id ?? null

  async function handleSync() {
    try {
      await syncMutation.mutateAsync()
      await refetch()
      if (signalsEnabled) {
        const { data: sig } = await refetchSignals()
        if (sig) {
          const summary = summarizeStrongSignals(sig.snapshot_id, sig.signals)
          if (summary) {
            maybeNotifyStrongSignals(summary)
          }
        }
      }
    } catch {
      // tracked via syncMutation
    }
  }

  if (isLoading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error && !data && signals.length === 0) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载建议：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  const structuralActions = data?.structural_actions ?? []
  const hasConsolidateBlock = structuralActions.some((item) => item.action === 'consolidate')
  const totalActions =
    (data?.sell_actions.length ?? 0) +
    (data?.buy_actions.length ?? 0) +
    (data?.explore_actions.length ?? 0)

  const signalsSummaryLabel = signalsEnabled
    ? signalsLoading
      ? '加载中…'
      : `${signals.length} 条`
    : null

  return (
    <div className="space-y-6">
      <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        以下建议由规则自动生成，仅供个人参考，<strong>非投资建议</strong>。请结合自身情况独立决策。
      </p>

      <div>
        <h2 className="text-2xl font-semibold text-slate-900">本周建议</h2>
        <p className="mt-1 text-sm text-slate-500">
          {snapshotId !== null
            ? `快照 #${snapshotId}${data?.data_as_of_date ? ` · 净值截至 ${data.data_as_of_date}` : ''}`
            : '导入持仓并同步数据后，系统会给出调仓建议'}
        </p>
      </div>

      {(syncMutation.isError || error || (signalsEnabled && signalsError)) ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {syncMutation.isError
            ? (syncMutation.error instanceof Error ? syncMutation.error.message : '同步失败')
            : (error instanceof Error
                ? error.message
                : signalsError instanceof Error
                  ? signalsError.message
                  : '未知错误')}
        </div>
      ) : null}

      {snapshotId === null ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <h3 className="text-xl font-semibold text-slate-900">还没有建议</h3>
          <p className="mt-2 text-slate-500">请先导入持仓并同步基金数据。</p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/import"
              className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              去导入持仓
            </Link>
            <button
              type="button"
              onClick={handleSync}
              disabled={syncMutation.isPending}
              className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {syncMutation.isPending ? '同步中...' : '同步数据'}
            </button>
          </div>
        </div>
      ) : (
        <>
          <StructuralAlerts items={structuralActions} />

          {totalActions === 0 && structuralActions.length === 0 ? (
            <p className="rounded-xl border border-slate-200 bg-white px-5 py-6 text-sm text-slate-500 shadow-sm">
              当前组合无需调整，保持观察即可。
            </p>
          ) : null}

          <ActionList
            title="建议卖出"
            items={data?.sell_actions ?? []}
            emptyText="暂无卖出建议"
            tone="sell"
          />
          {hasConsolidateBlock && (data?.buy_actions.length ?? 0) > 0 ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              下列加仓建议已暂停；请先处理上方的组合整理事项。
            </p>
          ) : null}
          <ActionList
            title="建议增配"
            items={data?.buy_actions ?? []}
            emptyText="暂无增配建议"
            tone="buy"
          />
          <ActionList
            title="可考虑新买（浏览参考，非配置建议）"
            items={data?.explore_actions ?? []}
            emptyText="暂无大类缺口或热点交叉机会"
            tone="explore"
          />

          <details
            className="rounded-xl border border-slate-200 bg-white shadow-sm"
            open={detailsOpen}
            onToggle={(event) => setDetailsOpen(event.currentTarget.open)}
          >
            <summary className="cursor-pointer px-5 py-4 text-base font-semibold text-slate-900">
              {signalsSummaryLabel
                ? `查看全部建议（${signalsSummaryLabel}）`
                : '查看全部建议'}
            </summary>
            <div className="border-t border-slate-200 px-2 pb-4">
              {signalsLoading ? (
                <p className="px-3 py-4 text-sm text-slate-500">加载中...</p>
              ) : signals.length === 0 ? (
                <p className="px-3 py-4 text-sm text-slate-500">暂无详细建议条目</p>
              ) : (
                <SignalsTable signals={signals} />
              )}
            </div>
          </details>

          <p className="text-sm text-slate-500">
            <Link to="/insights" className="font-medium text-indigo-600 hover:text-indigo-800">
              想了解为什么？查看深入分析 →
            </Link>
          </p>
        </>
      )}
    </div>
  )
}
