import { Link } from 'react-router-dom'
import { useOverview, useOpportunities, useHotThemes, useSyncLogs } from '../api/hooks'
import ActionSummaryCards from '../components/ActionSummaryCards'
import AllocationChart from '../components/AllocationChart'
import ConcentrationCard from '../components/ConcentrationCard'
import HotThemeRadar from '../components/HotThemeRadar'
import OnboardingGuide from '../components/OnboardingGuide'
import HoldingsTable from '../components/HoldingsTable'
import StatCard from '../components/StatCard'
import ThemeExposurePanel from '../components/ThemeExposurePanel'
import { formatCurrency, formatProfitAmount, formatSignedPercent } from '../utils/format'

export default function Dashboard() {
  const { data: overview, isLoading: loading, error } = useOverview()
  const { data: opportunities } = useOpportunities({
    sell_limit: 3,
    buy_limit: 3,
    explore_limit: 3,
    include_hot_themes: false,
  })
  const { data: hotThemes = [], isLoading: themesLoading } = useHotThemes({
    theme_limit: 5,
  })
  const { data: syncLogsData } = useSyncLogs(1)

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载组合概览：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  if (!overview || overview.holdings.length === 0) {
    return (
      <div className="space-y-6">
        <OnboardingGuide />
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
      </div>
    )
  }

  const profitTone =
    overview.total_profit > 0 ? 'profit' : overview.total_profit < 0 ? 'loss' : 'default'

  const lastSyncStatus = syncLogsData?.logs?.[0]?.status ?? null
  const statusDot = lastSyncStatus ? {
    done: { color: 'bg-emerald-400', label: '数据正常' },
    partial: { color: 'bg-amber-400', label: '部分数据同步失败' },
    failed: { color: 'bg-rose-400', label: '数据同步失败' },
    running: { color: 'bg-blue-400', label: '同步进行中' },
  }[lastSyncStatus] ?? null : null

  async function handleExportReport() {
    try {
      const response = await fetch('/api/report/weekly')
      const text = await response.text()
      const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `fund-report-${new Date().toISOString().slice(0, 10)}.md`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      // silently fail
    }
  }

  const opportunitiesWithThemes = opportunities
    ? { ...opportunities, hot_themes: hotThemes }
    : null

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">组合总览</h2>
          <p className="mt-1 text-sm text-slate-500">
            快照 #{overview.snapshot_id ?? '—'} · 共 {overview.holdings.length} 只基金
            {overview.data_as_of_date ? ` · 净值截至 ${overview.data_as_of_date}` : ''}
            {statusDot && (
              <span className="inline-flex items-center gap-1 ml-3" title={statusDot.label}>
                <span className={`inline-block h-2 w-2 rounded-full ${statusDot.color}`} />
                <span className="text-xs text-slate-400">{statusDot.label}</span>
              </span>
            )}
          </p>
        </div>
        {overview && overview.holdings.length > 0 && (
          <button
            type="button"
            onClick={handleExportReport}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
          >
            📥 导出周报
          </button>
        )}
      </div>

      <ActionSummaryCards data={opportunitiesWithThemes} />
      {themesLoading ? (
        <p className="text-sm text-slate-500">热点雷达加载中...</p>
      ) : (
        <HotThemeRadar themes={hotThemes} />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="总市值" value={formatCurrency(overview.total_value)} />
        <StatCard title="总成本" value={formatCurrency(overview.total_cost)} />
        <StatCard
          title="总盈亏"
          value={formatProfitAmount(overview.total_profit)}
          subtitle={formatSignedPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
        <StatCard
          title="收益率"
          value={formatSignedPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">大类配置</h3>
          <p className="mt-1 text-sm text-slate-500">按基金名称与类型自动分类</p>
          <div className="mt-4">
            <AllocationChart allocation={overview.category_allocation ?? []} />
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">主题暴露</h3>
          <p className="mt-1 text-sm text-slate-500">存储/CPO/半导体等赛道占比</p>
          <div className="mt-4">
            <ThemeExposurePanel allocation={overview.theme_allocation ?? []} />
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">集中度 Top5</h3>
        <p className="mt-1 text-sm text-slate-500">单只权重过高可能触发减仓信号</p>
        <div className="mt-4">
          <ConcentrationCard
            topHoldings={overview.top_holdings ?? []}
            concentrationTop5Pct={overview.concentration_top5_pct ?? 0}
          />
        </div>
      </section>

      <HoldingsTable holdings={overview.holdings} />
    </div>
  )
}
