import { Link, useSearchParams } from 'react-router-dom'
import { useOpportunities, useSyncData } from '../api/hooks'
import ActionList from '../components/ActionList'
import StructuralAlerts from '../components/StructuralAlerts'
import type { FundCandidate, HotTheme } from '../types'

type TabKey = 'actions' | 'themes'

function formatCandidateReturn(candidate: FundCandidate) {
  if (candidate.return_1m !== null && candidate.return_1m !== undefined) {
    return `近1月 ${candidate.return_1m.toFixed(2)}%`
  }
  if (candidate.return_1w !== null && candidate.return_1w !== undefined) {
    return `近1周 ${candidate.return_1w.toFixed(2)}%`
  }
  if (candidate.return_1y !== null && candidate.return_1y !== undefined) {
    return `近1年 ${candidate.return_1y.toFixed(2)}%`
  }
  return '—'
}

function ThemeCard({ theme }: { theme: HotTheme }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-slate-900">{theme.label}</p>
          <p className="mt-1 text-sm text-slate-500">
            组合 {theme.portfolio_weight_pct.toFixed(2)}%
            {theme.return_1m_median !== null
              ? ` · 近1月中位 ${theme.return_1m_median.toFixed(2)}%`
              : ''}
          </p>
        </div>
        {theme.aligned_gap && theme.aligned_category_label ? (
          <span className="inline-flex rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
            与{theme.aligned_category_label}低配一致
          </span>
        ) : null}
      </div>

      {theme.candidates.length > 0 ? (
        <ul className="mt-4 divide-y divide-slate-200 overflow-hidden rounded-md border border-slate-200">
          {theme.candidates.map((candidate) => (
            <li
              key={candidate.fund_code}
              className="flex items-center justify-between gap-3 bg-slate-50/60 px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium text-slate-900">{candidate.fund_name}</p>
                <p className="text-xs text-slate-500">{candidate.fund_code}</p>
              </div>
              <span className="font-medium tabular-nums text-slate-900">
                {formatCandidateReturn(candidate)}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-4 text-sm text-slate-500">暂无候选基金数据</p>
      )}
    </div>
  )
}

export default function OpportunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const activeTab: TabKey = tabParam === 'themes' ? 'themes' : 'actions'

  const { data, isLoading, error, refetch } = useOpportunities({
    sell_limit: 10,
    buy_limit: 10,
    explore_limit: 10,
    theme_limit: 9,
  })
  const syncMutation = useSyncData()

  function setTab(tab: TabKey) {
    setSearchParams({ tab })
  }

  async function handleSync() {
    try {
      await syncMutation.mutateAsync()
      await refetch()
    } catch {
      // error is tracked via syncMutation.isError
    }
  }

  if (isLoading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error && !data) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载机会数据：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  const snapshotId = data?.snapshot_id ?? null
  const structuralActions = data?.structural_actions ?? []
  const hasConsolidateBlock = structuralActions.some((item) => item.action === 'consolidate')
  const totalActions =
    (data?.sell_actions.length ?? 0) +
    (data?.buy_actions.length ?? 0) +
    (data?.explore_actions.length ?? 0)

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
        <p className="font-medium">免责声明</p>
        <p className="mt-1 text-amber-800">
          以下机会由量化规则自动生成，仅供个人参考，<strong>非投资建议</strong>
          。请结合自身风险承受能力独立决策。
        </p>
        <p className="mt-2 text-amber-800">
          热点按主题基金近 1 月收益中位数排序，反映近期业绩而非新闻舆情，仅供参考，不构成投资建议。
        </p>
      </div>

      <div>
        <h2 className="text-2xl font-semibold text-slate-900">机会中心</h2>
        <p className="mt-1 text-sm text-slate-500">
          {snapshotId !== null
            ? `快照 #${snapshotId}${data?.data_as_of_date ? ` · 净值截至 ${data.data_as_of_date}` : ''}`
            : '导入持仓并同步数据后，系统将聚合行动建议与热点主题'}
        </p>
      </div>

      {(syncMutation.isError || error) ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {syncMutation.isError
            ? (syncMutation.error instanceof Error ? syncMutation.error.message : '同步失败')
            : (error instanceof Error ? error.message : '未知错误')}
        </div>
      ) : null}

      {snapshotId === null ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <h3 className="text-xl font-semibold text-slate-900">暂无机会数据</h3>
          <p className="mt-2 text-slate-500">导入持仓并同步后查看机会</p>
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
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setTab('actions')}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === 'actions'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              行动清单
              <span className={activeTab === 'actions' ? 'text-slate-300' : 'text-slate-400'}>
                {' '}
                {totalActions}
              </span>
            </button>
            <button
              type="button"
              onClick={() => setTab('themes')}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                activeTab === 'themes'
                  ? 'bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              热点雷达
              <span className={activeTab === 'themes' ? 'text-slate-300' : 'text-slate-400'}>
                {' '}
                {data?.hot_themes.length ?? 0}
              </span>
            </button>
          </div>

          {activeTab === 'actions' ? (
            <div className="space-y-6">
              <StructuralAlerts items={structuralActions} />
              {totalActions === 0 && structuralActions.length === 0 ? (
                <p className="rounded-xl border border-slate-200 bg-white px-5 py-6 text-sm text-slate-500 shadow-sm">
                  暂无明确行动，组合配置较为均衡
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
                  以下增配已因持仓过多暂停；请先处理上方结构问题。
                </p>
              ) : null}
              <ActionList
                title="持仓增配"
                items={data?.buy_actions ?? []}
                emptyText="暂无增配建议"
                tone="buy"
              />
              <ActionList
                title="探索新买（浏览参考，非配置建议）"
                items={data?.explore_actions ?? []}
                emptyText="暂无大类缺口或热点交叉机会"
                tone="explore"
              />
            </div>
          ) : (
            <div className="space-y-4">
              {(data?.hot_themes.length ?? 0) === 0 ? (
                <p className="rounded-xl border border-slate-200 bg-white px-5 py-6 text-sm text-slate-500 shadow-sm">
                  热点数据暂不可用，请稍后同步
                </p>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {data?.hot_themes.map((theme) => (
                    <ThemeCard key={theme.theme} theme={theme} />
                  ))}
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
