import { useQuery } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import {
  useBacktestSensitivity,
  useBacktestSnapshotStats,
  useCorrelation,
  useMacroIndicators,
  useOpportunities,
  useOverview,
  useRisk,
  useStyleExposure,
} from '../api/hooks'
import { fetchThemeCandidates, fetchThemes, queryKeys } from '../api/queries'
import BacktestPanel from '../components/BacktestPanel'
import StatCard from '../components/StatCard'
import ThemeCard from '../components/ThemeCard'
import ThemeExposurePanel from '../components/ThemeExposurePanel'
import WhatIfPanel from '../components/WhatIfPanel'
import type { CorrelationOut } from '../types'

type TabKey = 'risk' | 'themes' | 'backtest'

function formatPercent(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`
}

function correlationColor(value: number) {
  if (value >= 0.85) return 'bg-rose-200 text-rose-900'
  if (value >= 0.6) return 'bg-orange-100 text-orange-900'
  if (value >= 0.3) return 'bg-amber-50 text-amber-900'
  if (value <= -0.3) return 'bg-sky-100 text-sky-900'
  return 'bg-slate-50 text-slate-700'
}

function CorrelationHeatmap({ data }: { data: CorrelationOut }) {
  if (data.labels.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        暂无足够净值数据计算相关性。请先在设置页同步基金数据。
      </p>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr>
            <th className="px-2 py-2 text-left text-slate-500" />
            {data.labels.map((label) => (
              <th key={label} className="px-2 py-2 text-center font-medium text-slate-600">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.labels.map((rowLabel, rowIndex) => (
            <tr key={rowLabel}>
              <td className="px-2 py-2 font-medium text-slate-600">{rowLabel}</td>
              {data.labels.map((_, colIndex) => {
                const value = data.matrix[rowIndex][colIndex]
                return (
                  <td
                    key={`${rowLabel}-${colIndex}`}
                    className={`px-2 py-2 text-center font-mono text-xs ${correlationColor(value)}`}
                  >
                    {value.toFixed(2)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-slate-500">
        基于近 {data.period_days} 个交易日共同净值序列的收益相关系数
      </p>
    </div>
  )
}

export default function InsightsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const activeTab: TabKey =
    tabParam === 'themes' ? 'themes' : tabParam === 'backtest' ? 'backtest' : 'risk'

  function setTab(tab: TabKey) {
    setSearchParams({ tab })
  }

  const {
    data: correlation,
    isLoading: corrLoading,
    error: corrError,
  } = useCorrelation()
  const {
    data: risk,
    isLoading: riskLoading,
    error: riskError,
  } = useRisk()
  const { data: sensitivity, error: sensError } = useBacktestSensitivity()
  const { data: snapshotStats, error: statsError } = useBacktestSnapshotStats()
  const { data: overview, error: overviewError } = useOverview()
  const { data: styleExposure } = useStyleExposure()
  const { data: macro } = useMacroIndicators()
  const { data: opportunities, isLoading: themesLoading } = useOpportunities({
    sell_limit: 0,
    buy_limit: 0,
    explore_limit: 0,
    theme_limit: 9,
    include_hot_themes: true,
  })
  const { data: themes = [], error: themesError } = useQuery({
    queryKey: queryKeys.themes,
    queryFn: fetchThemes,
  })

  const loading = corrLoading || riskLoading
  const themeAllocation = overview?.theme_allocation ?? []

  const errorMessages: string[] = []
  if (corrError) errorMessages.push('相关性')
  if (riskError) errorMessages.push('风险指标')
  if (overviewError) errorMessages.push('主题暴露')
  if (themesError) errorMessages.push('主题列表')

  let error: string | null = null
  if (errorMessages.length === 4) {
    const firstErr = corrError || riskError || overviewError || themesError
    error = firstErr instanceof Error ? firstErr.message : '加载失败'
  } else if (errorMessages.length > 0) {
    error = `部分数据加载失败：${errorMessages.join('、')}`
  }

  const backtestError =
    sensError || statsError
      ? '回测数据暂不可用，请确认后端已更新并重启服务'
      : null

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  const hasSnapshot = correlation?.snapshot_id !== null

  if (error && !hasSnapshot) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载分析数据：{error}
      </div>
    )
  }

  if (!hasSnapshot) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h2 className="text-xl font-semibold text-slate-900">还没有持仓数据</h2>
        <p className="mt-2 text-slate-500">导入持仓并同步净值后，可查看风险与主题分析。</p>
        <Link
          to="/import"
          className="mt-6 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          去导入持仓
        </Link>
      </div>
    )
  }

  const sharpeTone =
    risk?.sharpe !== null && risk?.sharpe !== undefined
      ? risk.sharpe > 0
        ? 'profit'
        : risk.sharpe < 0
          ? 'loss'
          : 'default'
      : 'default'

  const maxDdTone =
    risk?.max_dd !== null && risk?.max_dd !== undefined
      ? risk.max_dd < -0.1
        ? 'loss'
        : 'default'
      : 'default'

  return (
    <div className="space-y-6">
      {error ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          {error}
        </div>
      ) : null}

      <div>
        <h2 className="text-2xl font-semibold text-slate-900">深入了解</h2>
        <p className="mt-1 text-sm text-slate-500">
          快照 #{correlation?.snapshot_id ?? '—'} · 风险、主题与回测（进阶阅读）
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ['risk', '风险与相关性'],
            ['themes', '热点与主题'],
            ['backtest', '回测与模拟'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              activeTab === key
                ? 'bg-slate-900 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === 'risk' ? (
        <>
          {macro?.available && (
            <div
              className={`rounded-lg border px-4 py-3 text-sm ${
                macro.environment === 'tight'
                  ? 'border-rose-200 bg-rose-50 text-rose-800'
                  : macro.environment === 'loose'
                    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
                    : 'border-slate-200 bg-slate-50 text-slate-700'
              }`}
            >
              <span className="font-medium">宏观环境：</span>
              {macro.environment === 'tight' && '偏紧 —— 利率上行，可关注短久期债基'}
              {macro.environment === 'loose' && '偏松 —— 利率下行，风险资产相对友好'}
              {macro.environment === 'neutral' && '中性 —— 利率较稳定'}
            </div>
          )}

          <section>
            <h3 className="text-lg font-medium text-slate-900">组合风险</h3>
            {risk?.volatility === null ? (
              <p className="mt-3 text-sm text-slate-500">暂无足够净值数据，请先同步。</p>
            ) : (
              <div className="mt-4 grid gap-4 sm:grid-cols-3">
                <StatCard
                  title="年化波动率"
                  value={formatPercent(risk?.volatility ?? 0)}
                  subtitle={`近 ${risk?.period_days ?? 0} 个交易日`}
                />
                <StatCard
                  title="风险收益比"
                  value={(risk?.sharpe ?? 0).toFixed(2)}
                  subtitle="数值越高通常越好"
                  tone={sharpeTone}
                />
                <StatCard
                  title="最大回撤"
                  value={formatPercent(risk?.max_dd ?? 0)}
                  subtitle={`近 ${risk?.period_days ?? 0} 个交易日`}
                  tone={maxDdTone}
                />
              </div>
            )}
          </section>

          {styleExposure?.snapshot_id != null && (
            <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-medium text-slate-900">风格暴露</h3>
              <p className="mt-1 text-sm text-slate-500">基于基金名称自动分类，仅供参考</p>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <div>
                  <h4 className="mb-2 text-sm font-medium text-slate-700">规模</h4>
                  {Object.entries(styleExposure.size_exposure).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-slate-600">
                        {{ large_cap: '大盘', small_cap: '小盘', balanced: '均衡' }[key] || key}
                      </span>
                      <span className="font-mono text-slate-900">{val.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
                <div>
                  <h4 className="mb-2 text-sm font-medium text-slate-700">风格</h4>
                  {Object.entries(styleExposure.style_exposure).map(([key, val]) => (
                    <div key={key} className="flex justify-between text-sm">
                      <span className="text-slate-600">
                        {{ value: '价值', growth: '成长', balanced: '均衡' }[key] || key}
                      </span>
                      <span className="font-mono text-slate-900">{val.toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-medium text-slate-900">基金走势相似度</h3>
            <p className="mt-1 text-sm text-slate-500">数值越高表示走势越像，过高可能需要合并持仓</p>
            <div className="mt-4">{correlation ? <CorrelationHeatmap data={correlation} /> : null}</div>
          </section>
        </>
      ) : null}

      {activeTab === 'themes' ? (
        <div className="space-y-6">
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-medium text-slate-900">我的主题暴露</h3>
            <div className="mt-4">
              <ThemeExposurePanel allocation={themeAllocation} />
            </div>
          </section>

          <section>
            <h3 className="text-lg font-medium text-slate-900">近期热点主题</h3>
            <p className="mt-1 text-sm text-slate-500">
              按主题基金近 1 月收益中位数排序，仅供参考，不构成投资建议。
            </p>
            {themesLoading ? (
              <p className="mt-4 text-sm text-slate-500">加载中...</p>
            ) : (opportunities?.hot_themes.length ?? 0) === 0 ? (
              <p className="mt-4 rounded-xl border border-slate-200 bg-white px-5 py-6 text-sm text-slate-500 shadow-sm">
                热点数据暂不可用，请稍后同步
              </p>
            ) : (
              <div className="mt-4 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {opportunities?.hot_themes.map((theme) => (
                  <ThemeCard key={theme.theme} theme={theme} />
                ))}
              </div>
            )}
          </section>

          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-medium text-slate-900">探索其他主题</h3>
            <div className="mt-4 flex flex-wrap gap-2">
              {themes
                .filter((theme) =>
                  ['storage_semiconductor', 'cpo_optics', 'ai_compute'].includes(theme.theme),
                )
                .map((theme) => (
                  <button
                    key={theme.theme}
                    type="button"
                    onClick={() => void fetchThemeCandidates(theme.theme)}
                    className="rounded-full border border-slate-300 px-3 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                  >
                    {theme.label}
                  </button>
                ))}
            </div>
          </section>
        </div>
      ) : null}

      {activeTab === 'backtest' ? (
        <>
          <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-medium text-slate-900">历史建议回测</h3>
            {backtestError ? (
              <p className="mt-4 text-sm text-amber-800">{backtestError}</p>
            ) : null}
            <div className="mt-4">
              <BacktestPanel
                sensitivity={sensitivity ?? null}
                snapshotStats={snapshotStats ?? null}
              />
            </div>
          </section>
          <WhatIfPanel overview={overview ?? null} />
        </>
      ) : null}

      <p className="text-sm text-slate-500">
        <Link to="/advice" className="font-medium text-indigo-600 hover:text-indigo-800">
          ← 返回本周建议
        </Link>
      </p>
    </div>
  )
}
