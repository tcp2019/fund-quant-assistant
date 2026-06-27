import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  useBacktestSensitivity,
  useBacktestSnapshotStats,
  useCorrelation,
  useMacroIndicators,
  useOverview,
  useRisk,
  useStyleExposure,
} from '../api/hooks'
import { fetchThemeCandidates, fetchThemes, queryKeys } from '../api/queries'
import BacktestPanel from '../components/BacktestPanel'
import StatCard from '../components/StatCard'
import ThemeExposurePanel from '../components/ThemeExposurePanel'
import WhatIfPanel from '../components/WhatIfPanel'
import type { CorrelationOut } from '../types'

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
        暂无足够净值数据计算相关性。请先同步基金数据。
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

export default function AnalysisPage() {
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
  const {
    data: sensitivity,
    error: sensError,
  } = useBacktestSensitivity()
  const {
    data: snapshotStats,
    error: statsError,
  } = useBacktestSnapshotStats()
  const {
    data: overview,
    error: overviewError,
  } = useOverview()
  const { data: styleExposure } = useStyleExposure()
  const { data: macro } = useMacroIndicators()
  const {
    data: themes = [],
    error: themesError,
  } = useQuery({
    queryKey: queryKeys.themes,
    queryFn: fetchThemes,
  })

  const loading = corrLoading || riskLoading

  const themeAllocation = overview?.theme_allocation ?? []

  // Compose error state mirroring the original allSettled logic
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
        <p className="mt-2 text-slate-500">导入持仓并同步净值后，可查看相关性与风险指标。</p>
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

      {macro?.available && (
        <div className={`rounded-lg border px-4 py-3 text-sm ${
          macro.environment === 'tight' ? 'border-rose-200 bg-rose-50 text-rose-800' :
          macro.environment === 'loose' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' :
          'border-slate-200 bg-slate-50 text-slate-700'
        }`}>
          <span className="font-medium">宏观环境：</span>
          {macro.environment === 'tight' && '偏紧 —— 利率上行，Shibor高位，建议关注短久期债基'}
          {macro.environment === 'loose' && '偏松 —— 利率下行，Shibor低位，风险资产友好'}
          {macro.environment === 'neutral' && '中性 —— 利率稳定'}
          <span className="ml-4 text-xs opacity-70">
            10Y国债 {macro.bond_10y}% {macro.bond_10y_trend === 'rising' ? '↑' : macro.bond_10y_trend === 'falling' ? '↓' : '→'} | 隔夜Shibor {macro.shibor_overnight}%
          </span>
        </div>
      )}

      <div>
        <h2 className="text-2xl font-semibold text-slate-900">组合分析</h2>
        <p className="mt-1 text-sm text-slate-500">
          快照 #{correlation?.snapshot_id ?? '—'} · 相关性与风险指标
        </p>
      </div>

      <section>
        <h3 className="text-lg font-medium text-slate-900">风险指标</h3>
        {risk?.volatility === null ? (
          <p className="mt-3 text-sm text-slate-500">
            暂无足够净值数据。请在设置页或信号页触发数据同步。
          </p>
        ) : (
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <StatCard
              title="年化波动率"
              value={formatPercent(risk?.volatility ?? 0)}
              subtitle={`近 ${risk?.period_days ?? 0} 个交易日`}
            />
            <StatCard
              title="夏普比率"
              value={(risk?.sharpe ?? 0).toFixed(2)}
              subtitle="无风险利率假设 0%"
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

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">主题暴露与热点候选</h3>
        <p className="mt-1 text-sm text-slate-500">按日频排行查看存储/CPO 等主题近1月表现</p>
        <div className="mt-4">
          <ThemeExposurePanel allocation={themeAllocation} />
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">探索其他主题</h3>
        <div className="mt-4 flex flex-wrap gap-2">
          {themes
            .filter((theme) => ['storage_semiconductor', 'cpo_optics', 'ai_compute'].includes(theme.theme))
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
        <p className="mt-2 text-xs text-slate-500">
          在 Dashboard 主题卡片中可查看近1月候选详情。
        </p>
      </section>

      {styleExposure?.snapshot_id !== null && styleExposure?.snapshot_id !== undefined && (
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-medium text-slate-900">风格暴露</h3>
          <p className="mt-1 text-sm text-slate-500">基于基金名称关键词自动分类</p>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">规模暴露</h4>
              {Object.entries(styleExposure.size_exposure).map(([key, val]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-slate-600">{{large_cap: '大盘', small_cap: '小盘', balanced: '均衡'}[key] || key}</span>
                  <span className="font-mono text-slate-900">{val.toFixed(1)}%</span>
                </div>
              ))}
            </div>
            <div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">风格暴露</h4>
              {Object.entries(styleExposure.style_exposure).map(([key, val]) => (
                <div key={key} className="flex justify-between text-sm">
                  <span className="text-slate-600">{{value: '价值', growth: '成长', balanced: '均衡'}[key] || key}</span>
                  <span className="font-mono text-slate-900">{val.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">规则回测与校验</h3>
        {backtestError ? (
          <p className="mt-4 text-sm text-amber-800">{backtestError}</p>
        ) : null}
        <div className="mt-4">
          <BacktestPanel sensitivity={sensitivity ?? null} snapshotStats={snapshotStats ?? null} />
        </div>
      </section>

      <WhatIfPanel overview={overview ?? null} />

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">收益相关性</h3>
        <div className="mt-4">
          {correlation ? <CorrelationHeatmap data={correlation} /> : null}
        </div>
      </section>
    </div>
  )
}
