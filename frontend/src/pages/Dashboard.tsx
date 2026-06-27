import { Link } from 'react-router-dom'
import { useState } from 'react'
import { useDailyHistory, useOverviewLive, useOpportunities, useSyncLogs } from '../api/hooks'
import AdviceSummary from '../components/AdviceSummary'
import AllocationChart from '../components/AllocationChart'
import ConcentrationCard from '../components/ConcentrationCard'
import DailyProfitChart from '../components/DailyProfitChart'
import NavAnomalyBanner from '../components/NavAnomalyBanner'
import OnboardingGuide from '../components/OnboardingGuide'
import HoldingsTable from '../components/HoldingsTable'
import StatCard from '../components/StatCard'
import { formatCurrency, formatProfitAmount, formatSignedPercent } from '../utils/format'

export default function Dashboard() {
  const [historyDays, setHistoryDays] = useState(30)
  const { data: overview, isLoading: loading, error } = useOverviewLive()
  const { data: dailyHistory, isLoading: historyLoading } = useDailyHistory(historyDays)
  const { data: opportunities } = useOpportunities({
    sell_limit: 1,
    buy_limit: 1,
    explore_limit: 0,
    include_hot_themes: false,
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
            通过截图导入或手动录入第一笔持仓，即可在这里查看总览。
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

  const hasRealtime = Boolean(
    overview.current_total_value && overview.current_total_value > 0 && overview.nav_date,
  )
  const currentProfitTone =
    (overview.current_total_profit ?? 0) > 0
      ? 'profit'
      : (overview.current_total_profit ?? 0) < 0
        ? 'loss'
        : 'default'

  const hasDailyProfit =
    overview.daily_total_profit !== null && overview.daily_total_profit !== undefined
  const dailyProfitTone =
    (overview.daily_total_profit ?? 0) > 0
      ? 'profit'
      : (overview.daily_total_profit ?? 0) < 0
        ? 'loss'
        : 'default'

  const dailyCompareDates = [
    ...new Set(
      overview.holdings
        .filter((h) => h.shares > 0 && h.prev_nav_date)
        .map((h) => h.prev_nav_date as string),
    ),
  ]
  const dailyCompareLabel =
    dailyCompareDates.length === 1 ? dailyCompareDates[0] : '上一交易日'

  const lastSyncStatus = syncLogsData?.logs?.[0]?.status ?? null
  const statusDot = lastSyncStatus
    ? ({
        done: { color: 'bg-emerald-400', label: '数据正常' },
        partial: { color: 'bg-amber-400', label: '部分数据同步失败' },
        failed: { color: 'bg-rose-400', label: '数据同步失败' },
        running: { color: 'bg-blue-400', label: '同步进行中' },
      }[lastSyncStatus] ?? null)
    : null

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">组合总览</h2>
          <p className="mt-1 text-sm text-slate-500">
            快照 #{overview.snapshot_id ?? '—'} · 共 {overview.holdings.length} 只基金
            {overview.nav_date
              ? ` · 净值截至 ${overview.nav_date}`
              : overview.data_as_of_date
                ? ` · 净值截至 ${overview.data_as_of_date}`
                : ''}
            {statusDot && (
              <span className="inline-flex items-center gap-1 ml-3" title={statusDot.label}>
                <span className={`inline-block h-2 w-2 rounded-full ${statusDot.color}`} />
                <span className="text-xs text-slate-400">{statusDot.label}</span>
              </span>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={handleExportReport}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 whitespace-nowrap"
        >
          📥 导出周报
        </button>
      </div>

      <NavAnomalyBanner anomalies={overview.nav_anomalies ?? []} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          title={hasRealtime ? '实时市值' : '总市值'}
          value={formatCurrency(hasRealtime ? overview.current_total_value! : overview.total_value)}
          subtitle={
            hasRealtime ? `导入时 ${formatCurrency(overview.total_value)}` : undefined
          }
        />
        <StatCard title="总成本" value={formatCurrency(overview.total_cost)} />
        <StatCard
          title="今日盈亏"
          value={
            hasDailyProfit ? formatProfitAmount(overview.daily_total_profit!) : '—'
          }
          subtitle={
            hasDailyProfit && overview.nav_date
              ? `较 ${dailyCompareLabel}`
              : '需全部持仓有两个交易日净值'
          }
          tone={hasDailyProfit ? dailyProfitTone : 'default'}
        />
        <StatCard
          title={hasRealtime ? '累计盈亏' : '总盈亏'}
          value={formatProfitAmount(
            hasRealtime ? overview.current_total_profit! : overview.total_profit,
          )}
          subtitle={
            hasRealtime
              ? `快照 ${formatSignedPercent(overview.total_profit_rate)}`
              : formatSignedPercent(overview.total_profit_rate)
          }
          tone={hasRealtime ? currentProfitTone : profitTone}
        />
        <StatCard
          title="收益率"
          value={formatSignedPercent(
            hasRealtime ? overview.current_total_profit_rate! : overview.total_profit_rate,
          )}
          tone={hasRealtime ? currentProfitTone : profitTone}
        />
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-semibold text-slate-900">近期日盈亏</h3>
            <p className="mt-1 text-sm text-slate-500">按各基金相邻交易日净值估算，与「今日盈亏」算法一致</p>
          </div>
          <div className="flex rounded-lg border border-slate-200 p-0.5 text-sm">
            {([30, 90] as const).map((days) => (
              <button
                key={days}
                type="button"
                onClick={() => setHistoryDays(days)}
                className={`rounded-md px-3 py-1.5 font-medium transition-colors ${
                  historyDays === days
                    ? 'bg-slate-900 text-white'
                    : 'text-slate-600 hover:bg-slate-50'
                }`}
              >
                {days} 天
              </button>
            ))}
          </div>
        </div>
        <div className="mt-4">
          {historyLoading ? (
            <p className="text-sm text-slate-500">加载曲线...</p>
          ) : (
            <DailyProfitChart
              points={dailyHistory?.points ?? []}
              days={dailyHistory?.days ?? historyDays}
            />
          )}
        </div>
      </section>

      <AdviceSummary data={opportunities ?? null} />

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">大类配置</h3>
        <p className="mt-1 text-sm text-slate-500">看看股票、债券等是否均衡</p>
        <div className="mt-4">
          <AllocationChart allocation={overview.category_allocation ?? []} />
        </div>
      </section>

      <details className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <summary className="cursor-pointer px-6 py-4 text-base font-semibold text-slate-900">
          持仓与集中度
        </summary>
        <div className="space-y-6 border-t border-slate-200 px-6 pb-6 pt-4">
          <div>
            <h4 className="text-sm font-medium text-slate-700">集中度 Top5</h4>
            <p className="mt-1 text-sm text-slate-500">单只占比过高时会提示减仓</p>
            <div className="mt-4">
              <ConcentrationCard
                topHoldings={overview.top_holdings ?? []}
                concentrationTop5Pct={overview.concentration_top5_pct ?? 0}
              />
            </div>
          </div>
          <HoldingsTable holdings={overview.holdings} />
          <Link
            to="/holdings"
            className="inline-block text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            查看完整持仓与快照历史 →
          </Link>
        </div>
      </details>

      <div className="flex flex-wrap gap-4 text-sm">
        <Link to="/advice" className="font-medium text-indigo-600 hover:text-indigo-800">
          查看本周建议 →
        </Link>
        <Link to="/insights" className="font-medium text-slate-600 hover:text-slate-900">
          深入了解组合风险 →
        </Link>
      </div>
    </div>
  )
}
