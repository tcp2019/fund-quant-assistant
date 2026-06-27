import { Link } from 'react-router-dom'
import { useSignals, useSyncData } from '../api/hooks'
import SignalsTable from '../components/SignalsTable'
import type { Signal } from '../types'
import { maybeNotifyStrongSignals, summarizeStrongSignals } from '../utils/notifications'

function sortSignals(signals: Signal[]) {
  return [...signals].sort((a, b) => b.score - a.score)
}

export default function SignalsPage() {
  const { data, isLoading, error, refetch } = useSignals()
  const syncMutation = useSyncData()

  const signals = data?.signals ? sortSignals(data.signals) : []
  const snapshotId = data?.snapshot_id ?? null

  async function handleSync() {
    try {
      await syncMutation.mutateAsync()
      const { data: freshData } = await refetch()
      if (freshData) {
        const summary = summarizeStrongSignals(freshData.snapshot_id, freshData.signals)
        if (summary) {
          maybeNotifyStrongSignals(summary)
        }
      }
    } catch {
      // error is tracked via syncMutation.isError / syncMutation.error
    }
  }

  if (isLoading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error && signals.length === 0 && snapshotId === null) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载信号：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
        <p className="font-medium">免责声明</p>
        <p className="mt-1 text-amber-800">
          以下信号由量化规则自动生成，仅供个人参考，<strong>非投资建议</strong>
          。请结合自身风险承受能力独立决策。
        </p>
      </div>

      <div>
        <h2 className="text-2xl font-semibold text-slate-900">买卖信号</h2>
        <p className="mt-1 text-sm text-slate-500">
          {snapshotId !== null
            ? `快照 #${snapshotId} · 共 ${signals.length} 条信号，按综合得分排序`
            : '导入持仓并同步数据后，系统将生成再平衡与风险信号'}
        </p>
      </div>

      {(syncMutation.isError || error) ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {syncMutation.isError
            ? (syncMutation.error instanceof Error ? syncMutation.error.message : '同步失败')
            : (error instanceof Error ? error.message : '未知错误')}
        </div>
      ) : null}

      {signals.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <h3 className="text-xl font-semibold text-slate-900">暂无买卖信号</h3>
          <p className="mt-2 text-slate-500">
            请先导入持仓，再触发数据同步以计算量化信号。
          </p>
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
        <SignalsTable signals={signals} />
      )}
    </div>
  )
}
