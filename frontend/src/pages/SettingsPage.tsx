import { useCallback, useEffect, useState } from 'react'
import { fetchStrategy, syncData, updateStrategy } from '../api/client'
import type { StrategyConfig } from '../types'

const TEMPLATE_OPTIONS = [
  { value: 'conservative', label: '保守型' },
  { value: 'balanced', label: '均衡型' },
  { value: 'aggressive', label: '进取型' },
  { value: 'custom', label: '自定义' },
] as const

const CATEGORY_LABELS: Record<string, string> = {
  stock: '股票型',
  bond: '债券型',
  money: '货币/理财',
  qdii: 'QDII/海外',
  other: '其他',
}

const PRESET_WEIGHTS: Record<string, Record<string, number>> = {
  conservative: {
    stock: 0.2,
    bond: 0.5,
    money: 0.2,
    qdii: 0.05,
    other: 0.05,
  },
  balanced: {
    stock: 0.4,
    bond: 0.3,
    money: 0.15,
    qdii: 0.1,
    other: 0.05,
  },
  aggressive: {
    stock: 0.6,
    bond: 0.15,
    money: 0.05,
    qdii: 0.15,
    other: 0.05,
  },
}

function formatWeightPct(value: number) {
  return `${(value * 100).toFixed(0)}%`
}

export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [templateName, setTemplateName] = useState('balanced')
  const [targetWeights, setTargetWeights] = useState<Record<string, number>>({})
  const [rebalanceDeviation, setRebalanceDeviation] = useState(5)
  const [singleFundMax, setSingleFundMax] = useState(25)

  const applyConfig = useCallback((config: StrategyConfig) => {
    setTemplateName(config.template_name)
    setTargetWeights(config.target_weights)
    setRebalanceDeviation(config.thresholds.rebalance_deviation_pct)
    setSingleFundMax(config.thresholds.single_fund_max_pct)
  }, [])

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const config = await fetchStrategy()
        if (!cancelled) {
          applyConfig(config)
          setError(null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载失败')
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [applyConfig])

  function handleTemplateChange(value: string) {
    setTemplateName(value)
    if (value !== 'custom' && PRESET_WEIGHTS[value]) {
      setTargetWeights(PRESET_WEIGHTS[value])
    }
  }

  function handleWeightChange(category: string, pct: number) {
    setTargetWeights((prev) => ({
      ...prev,
      [category]: pct / 100,
    }))
  }

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const body: Parameters<typeof updateStrategy>[0] = {
        template_name: templateName,
        thresholds: {
          rebalance_deviation_pct: rebalanceDeviation,
          rebalance_force_days: 365,
          single_fund_max_pct: singleFundMax,
          correlation_max: 0.85,
        },
      }
      if (templateName === 'custom') {
        body.target_weights = targetWeights
      }
      const config = await updateStrategy(body)
      applyConfig(config)
      setSuccess('策略已保存，信号已重新计算')
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  async function handleSync() {
    setSyncing(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await syncData()
      setSuccess(`数据同步完成，已更新 ${result.synced} 只基金`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '同步失败')
    } finally {
      setSyncing(false)
    }
  }

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  const isCustom = templateName === 'custom'
  const weightSum = Object.values(targetWeights).reduce((sum, value) => sum + value, 0)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">设置</h2>
        <p className="mt-1 text-sm text-slate-500">配置目标资产配置与信号阈值</p>
      </div>

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {success}
        </div>
      ) : null}

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">策略模板</h3>
        <p className="mt-1 text-sm text-slate-500">选择预设模板或自定义各类资产目标占比</p>

        <div className="mt-4">
          <label htmlFor="template" className="block text-sm font-medium text-slate-700">
            模板
          </label>
          <select
            id="template"
            value={templateName}
            onChange={(event) => handleTemplateChange(event.target.value)}
            className="mt-1 block w-full max-w-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          >
            {TEMPLATE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-6">
          <h4 className="text-sm font-medium text-slate-700">目标权重</h4>
          <div className="mt-3 space-y-3">
            {Object.entries(CATEGORY_LABELS).map(([category, label]) => (
              <div key={category} className="flex items-center gap-4">
                <span className="w-24 text-sm text-slate-600">{label}</span>
                {isCustom ? (
                  <div className="flex flex-1 items-center gap-3">
                    <input
                      type="range"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((targetWeights[category] ?? 0) * 100)}
                      onChange={(event) =>
                        handleWeightChange(category, Number(event.target.value))
                      }
                      className="flex-1"
                    />
                    <span className="w-12 text-right font-mono text-sm text-slate-700">
                      {Math.round((targetWeights[category] ?? 0) * 100)}%
                    </span>
                  </div>
                ) : (
                  <span className="font-mono text-sm text-slate-700">
                    {formatWeightPct(targetWeights[category] ?? 0)}
                  </span>
                )}
              </div>
            ))}
          </div>
          {isCustom ? (
            <p
              className={`mt-2 text-xs ${Math.abs(weightSum - 1) < 0.01 ? 'text-slate-500' : 'text-rose-600'}`}
            >
              合计 {Math.round(weightSum * 100)}%（需等于 100%）
            </p>
          ) : null}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">信号阈值</h3>
        <p className="mt-1 text-sm text-slate-500">调整再平衡与集中度触发条件</p>

        <div className="mt-4 space-y-5">
          <div>
            <label htmlFor="rebalance-deviation" className="block text-sm font-medium text-slate-700">
              再平衡偏差阈值
            </label>
            <p className="text-xs text-slate-500">类别实际占比与目标偏差超过此值时触发信号</p>
            <div className="mt-2 flex items-center gap-3">
              <input
                id="rebalance-deviation"
                type="range"
                min={1}
                max={20}
                step={0.5}
                value={rebalanceDeviation}
                onChange={(event) => setRebalanceDeviation(Number(event.target.value))}
                className="flex-1"
              />
              <span className="w-14 text-right font-mono text-sm text-slate-700">
                {rebalanceDeviation}%
              </span>
            </div>
          </div>

          <div>
            <label htmlFor="single-fund-max" className="block text-sm font-medium text-slate-700">
              单只基金上限
            </label>
            <p className="text-xs text-slate-500">单只基金持仓占比超过此值时触发减仓信号</p>
            <div className="mt-2 flex items-center gap-3">
              <input
                id="single-fund-max"
                type="range"
                min={10}
                max={50}
                step={1}
                value={singleFundMax}
                onChange={(event) => setSingleFundMax(Number(event.target.value))}
                className="flex-1"
              />
              <span className="w-14 text-right font-mono text-sm text-slate-700">
                {singleFundMax}%
              </span>
            </div>
          </div>
        </div>
      </section>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || (isCustom && Math.abs(weightSum - 1) >= 0.01)}
          className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? '保存中...' : '保存策略'}
        </button>
        <button
          type="button"
          onClick={handleSync}
          disabled={syncing}
          className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {syncing ? '同步中...' : '同步数据'}
        </button>
      </div>
    </div>
  )
}
