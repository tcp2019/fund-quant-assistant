import { useCallback, useEffect, useState } from 'react'
import { refreshFundCatalog, testLlmConnection, updateStrategy } from '../api/client'
import { useStrategy, useSyncData, useSyncLogs } from '../api/hooks'
import type { Holding, Overview, StrategyConfig } from '../types'
import {
  enableNotificationsWithPermission,
  getNotificationsEnabled,
  notificationsSupported,
  permissionErrorMessage,
  permissionRecoveryHint,
  permissionStatusLabel,
  setNotificationsEnabled,
  showTestNotification,
  syncNotificationPreferenceWithPermission,
  systemNotificationVisibilityHint,
  type DesktopNotificationPayload,
  type NotificationPermissionState,
} from '../utils/notifications'
import {
  DEFAULT_LLM_BASE_URL,
  DEFAULT_LLM_MODEL,
  getLlmApiKey,
  getLlmBaseUrl,
  getLlmModel,
  saveLlmSettings,
} from '../utils/llmSettings'

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

const INTRA_CATEGORY_OPTIONS = [
  { value: 'equal', label: '类内等权目标' },
  { value: 'pro_rata', label: '按现占比维持结构' },
  { value: 'custom', label: '自定义类内权重' },
] as const

function formatWeightPct(value: number) {
  return `${(value * 100).toFixed(0)}%`
}

export default function SettingsPage() {
  // ── Query hooks ──
  const {
    data: strategyData,
    isLoading: strategyLoading,
    error: strategyError,
  } = useStrategy()
  const syncMutation = useSyncData()
  const { data: syncLogsData } = useSyncLogs(3)

  // ── Local state ──
  const [saving, setSaving] = useState(false)
  const [refreshingCatalog, setRefreshingCatalog] = useState(false)
  const [notificationsEnabled, setNotificationsEnabledState] = useState(false)
  const [notificationPermission, setNotificationPermission] =
    useState<NotificationPermissionState>('default')
  const [notificationPreview, setNotificationPreview] = useState<DesktopNotificationPayload | null>(
    null,
  )
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [templateName, setTemplateName] = useState('balanced')
  const [targetWeights, setTargetWeights] = useState<Record<string, number>>({})
  const [rebalanceDeviation, setRebalanceDeviation] = useState(5)
  const [singleFundMax, setSingleFundMax] = useState(25)
  const [minSuggestedTrade, setMinSuggestedTrade] = useState(500)
  const [maxFundsPerCategory, setMaxFundsPerCategory] = useState(10)
  const [intraCategoryMode, setIntraCategoryMode] =
    useState<StrategyConfig['intra_category_mode']>('equal')
  const [fundTargetWeights, setFundTargetWeights] = useState<Record<string, number>>({})
  const [holdingsForCustom, setHoldingsForCustom] = useState<Holding[]>([])
  const [llmApiKey, setLlmApiKey] = useState('')
  const [llmBaseUrl, setLlmBaseUrl] = useState(DEFAULT_LLM_BASE_URL)
  const [llmModel, setLlmModel] = useState(DEFAULT_LLM_MODEL)
  const [llmTesting, setLlmTesting] = useState(false)
  const [llmDialog, setLlmDialog] = useState<{ ok: boolean; title: string; message: string } | null>(
    null,
  )

  const applyConfig = useCallback((config: StrategyConfig) => {
    setTemplateName(config.template_name)
    setTargetWeights(config.target_weights)
    setRebalanceDeviation(config.thresholds.rebalance_deviation_pct)
    setSingleFundMax(config.thresholds.single_fund_max_pct)
    setMinSuggestedTrade(config.thresholds.min_suggested_trade_cny ?? 500)
    setMaxFundsPerCategory(config.thresholds.max_funds_per_category ?? 10)
    setIntraCategoryMode(config.intra_category_mode ?? 'equal')
    setFundTargetWeights(config.fund_target_weights ?? {})
  }, [])

  // Apply strategy data from query hook
  useEffect(() => {
    if (strategyData) {
      applyConfig(strategyData)
    }
  }, [strategyData, applyConfig])

  // Surface strategy loading error
  useEffect(() => {
    if (strategyError) {
      setError(strategyError instanceof Error ? strategyError.message : '加载失败')
    }
  }, [strategyError])

  useEffect(() => {
    setLlmApiKey(getLlmApiKey())
    setLlmBaseUrl(getLlmBaseUrl())
    setLlmModel(getLlmModel())
  }, [])

  useEffect(() => {
    const permission = syncNotificationPreferenceWithPermission()
    setNotificationPermission(permission)
    setNotificationsEnabledState(getNotificationsEnabled())
  }, [])

  useEffect(() => {
    function refreshPermission() {
      const permission = syncNotificationPreferenceWithPermission()
      setNotificationPermission(permission)
      setNotificationsEnabledState(getNotificationsEnabled())
    }

    window.addEventListener('focus', refreshPermission)
    document.addEventListener('visibilitychange', refreshPermission)
    return () => {
      window.removeEventListener('focus', refreshPermission)
      document.removeEventListener('visibilitychange', refreshPermission)
    }
  }, [])

  useEffect(() => {
    if (intraCategoryMode !== 'custom') {
      return
    }
    let cancelled = false
    async function loadHoldings() {
      try {
        const overview = await fetch('/api/portfolio/holdings').then(
          (r) => r.json() as Promise<Overview>,
        )
        if (!cancelled) {
          setHoldingsForCustom(overview.holdings ?? [])
        }
      } catch {
        if (!cancelled) {
          setHoldingsForCustom([])
        }
      }
    }
    void loadHoldings()
    return () => {
      cancelled = true
    }
  }, [intraCategoryMode])

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

  function handleFundTargetWeightChange(fundCode: string, pct: number) {
    setFundTargetWeights((prev) => ({
      ...prev,
      [fundCode]: pct / 100,
    }))
  }

  async function handleSave() {
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const body: Parameters<typeof updateStrategy>[0] = {
        template_name: templateName,
        intra_category_mode: intraCategoryMode,
        thresholds: {
          rebalance_deviation_pct: rebalanceDeviation,
          rebalance_force_days: 365,
          single_fund_max_pct: singleFundMax,
          correlation_max: 0.85,
          min_suggested_trade_cny: minSuggestedTrade,
          max_funds_per_category: maxFundsPerCategory,
        },
      }
      if (templateName === 'custom') {
        body.target_weights = targetWeights
      }
      if (intraCategoryMode === 'custom') {
        body.fund_target_weights = fundTargetWeights
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
    setError(null)
    setSuccess(null)
    try {
      const result = await syncMutation.mutateAsync(undefined)
      setSuccess(
        `数据同步完成，已更新 ${result.synced} 只基金` +
          (result.as_of_date ? `，净值截至 ${result.as_of_date}` : '') +
          (result.revalued ? `，重算市值 ${result.revalued} 条` : ''),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : '同步失败')
    }
  }

  async function handleRefreshCatalog() {
    setRefreshingCatalog(true)
    setError(null)
    setSuccess(null)
    try {
      const result = await refreshFundCatalog()
      setSuccess(`基金目录已刷新，共 ${result.count} 条记录`)
    } catch (err) {
      setError(err instanceof Error ? err.message : '刷新基金目录失败')
    } finally {
      setRefreshingCatalog(false)
    }
  }

  function handleSaveLlmSettings() {
    saveLlmSettings(llmApiKey, llmBaseUrl, llmModel)
    setLlmDialog({
      ok: true,
      title: '已保存',
      message: 'AI 解读设置已保存到本机浏览器',
    })
  }

  async function handleTestLlmConnection() {
    setLlmTesting(true)
    try {
      const result = await testLlmConnection({
        ...(llmApiKey.trim() ? { api_key: llmApiKey.trim() } : {}),
        base_url: llmBaseUrl.trim() || DEFAULT_LLM_BASE_URL,
        model: llmModel.trim() || DEFAULT_LLM_MODEL,
      })
      if (result.ok) {
        saveLlmSettings(llmApiKey, llmBaseUrl, llmModel)
        setLlmDialog({
          ok: true,
          title: '连接成功',
          message: 'LLM 连接成功，设置已保存到本机浏览器',
        })
      } else {
        setLlmDialog({
          ok: false,
          title: '连接失败',
          message: result.error ?? '连接失败',
        })
      }
    } catch (err) {
      setLlmDialog({
        ok: false,
        title: '连接失败',
        message: err instanceof Error ? err.message : '连接测试失败',
      })
    } finally {
      setLlmTesting(false)
    }
  }

  async function handleRequestNotificationPermission() {
    setError(null)
    setSuccess(null)
    const permission = await enableNotificationsWithPermission()
    setNotificationPermission(permission)
    setNotificationsEnabledState(getNotificationsEnabled())

    if (permission === 'granted') {
      setSuccess('已授权并开启强信号浏览器通知')
      return
    }
    setError(permissionErrorMessage(permission))
  }

  function handleDisableNotifications() {
    setNotificationsEnabled(false)
    setNotificationsEnabledState(false)
    setSuccess('已关闭浏览器通知（权限仍保留，可随时重新开启）')
    setError(null)
  }

  async function handleTestNotification() {
    setError(null)
    setSuccess(null)
    setNotificationPreview(null)

    const payload: DesktopNotificationPayload = {
      title: '基金持仓管家',
      body: '通知功能已开启。强买卖信号将在数据同步后出现提醒。',
    }

    try {
      const result = await showTestNotification()
      setNotificationPreview(payload)

      if (result.shown) {
        setSuccess('系统通知横幅已触发。若仍未看到，请查看右上角通知中心或下方 macOS 设置说明。')
        return
      }

      if (result.errorMessage) {
        setError(result.errorMessage)
      }
      setSuccess('已在下方展示应用内预览。桌面横幅可能被 macOS 设为「仅通知中心」，请按说明调整。')
    } catch (err) {
      setError(err instanceof Error ? err.message : '测试通知失败')
    }
  }

  if (strategyLoading) {
    return <p className="text-slate-500">加载中...</p>
  }

  const isCustom = templateName === 'custom'
  const weightSum = Object.values(targetWeights).reduce((sum, value) => sum + value, 0)
  const fundWeightSum = Object.values(fundTargetWeights).reduce((sum, value) => sum + value, 0)
  const customWeightsValid =
    intraCategoryMode !== 'custom' || Math.abs(fundWeightSum - 1) < 0.01

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">设置</h2>
        <p className="mt-1 text-sm text-slate-500">风险偏好、数据同步与通知</p>
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
        <h3 className="text-lg font-medium text-slate-900">风险偏好</h3>
        <p className="mt-1 text-sm text-slate-500">选择保守、均衡或进取，决定各类资产的目标占比</p>

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
          {isCustom ? (
            <>
              <h4 className="text-sm font-medium text-slate-700">自定义大类权重</h4>
              <div className="mt-3 space-y-3">
                {Object.entries(CATEGORY_LABELS).map(([category, label]) => (
                  <div key={category} className="flex items-center gap-4">
                    <span className="w-24 text-sm text-slate-600">{label}</span>
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
                  </div>
                ))}
              </div>
              <p
                className={`mt-2 text-xs ${Math.abs(weightSum - 1) < 0.01 ? 'text-slate-500' : 'text-rose-600'}`}
              >
                合计 {Math.round(weightSum * 100)}%（需等于 100%）
              </p>
            </>
          ) : (
            <>
              <h4 className="text-sm font-medium text-slate-700">目标占比一览</h4>
              <div className="mt-3 space-y-3">
                {Object.entries(CATEGORY_LABELS).map(([category, label]) => (
                  <div key={category} className="flex items-center gap-4">
                    <span className="w-24 text-sm text-slate-600">{label}</span>
                    <span className="font-mono text-sm text-slate-700">
                      {formatWeightPct(targetWeights[category] ?? 0)}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">AI 信号解读</h3>
        <p className="mt-1 text-sm text-slate-500">
          在「本周建议」中点击 AI 解读，用通俗语言解释信号含义。Key 仅保存在本机浏览器，不会写入服务器。
        </p>

        <div className="mt-4 space-y-4">
          <div>
            <label htmlFor="llm-api-key" className="block text-sm font-medium text-slate-700">
              API Key
            </label>
            <input
              id="llm-api-key"
              type="password"
              value={llmApiKey}
              onChange={(event) => setLlmApiKey(event.target.value)}
              placeholder="sk-..."
              className="mt-1 block w-full max-w-lg rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
          </div>

          <div>
            <label htmlFor="llm-base-url" className="block text-sm font-medium text-slate-700">
              接口地址
            </label>
            <input
              id="llm-base-url"
              type="url"
              value={llmBaseUrl}
              onChange={(event) => setLlmBaseUrl(event.target.value)}
              placeholder={DEFAULT_LLM_BASE_URL}
              className="mt-1 block w-full max-w-lg rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
            <p className="mt-1 text-xs text-slate-500">
              OpenAI 兼容接口。DeepSeek 填 https://api.deepseek.com，OpenAI 填 https://api.openai.com/v1
            </p>
          </div>

          <div>
            <label htmlFor="llm-model" className="block text-sm font-medium text-slate-700">
              模型
            </label>
            <input
              id="llm-model"
              type="text"
              value={llmModel}
              onChange={(event) => setLlmModel(event.target.value)}
              placeholder={DEFAULT_LLM_MODEL}
              className="mt-1 block w-full max-w-lg rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleSaveLlmSettings}
              className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              保存设置
            </button>
            <button
              type="button"
              onClick={() => void handleTestLlmConnection()}
              disabled={llmTesting}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {llmTesting ? '测试中...' : '测试连接'}
            </button>
          </div>
        </div>
      </section>

      <details className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <summary className="cursor-pointer px-6 py-4 text-lg font-medium text-slate-900">
          高级策略设置（懂再开）
        </summary>
        <div className="space-y-6 border-t border-slate-200 px-6 pb-6 pt-4">
        <div>
          <label htmlFor="intra-category-mode" className="block text-sm font-medium text-slate-700">
            类内增配分配
          </label>
          <p className="mt-1 text-xs text-slate-500">
            大类缺口如何拆到同类持仓：等权目标（默认）或按现占比维持结构
          </p>
          <select
            id="intra-category-mode"
            value={intraCategoryMode}
            onChange={(event) =>
              setIntraCategoryMode(event.target.value as StrategyConfig['intra_category_mode'])
            }
            className="mt-2 block w-full max-w-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-1 focus:ring-slate-500"
          >
            {INTRA_CATEGORY_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {intraCategoryMode === 'custom' ? (
          <div className="mt-6">
            <h4 className="text-sm font-medium text-slate-700">类内自定义权重</h4>
            <p className="mt-1 text-xs text-slate-500">
              为当前持仓指定类内目标权重，合计须为 100%（未列出的同类基金将等分剩余）
            </p>
            {holdingsForCustom.length === 0 ? (
              <p className="mt-3 text-sm text-slate-500">暂无持仓，请先导入</p>
            ) : (
              <div className="mt-3 space-y-3">
                {holdingsForCustom.map((holding) => (
                  <div key={holding.fund_code} className="flex items-center gap-4">
                    <span className="min-w-0 flex-1 truncate text-sm text-slate-600">
                      {holding.fund_name}
                      <span className="ml-2 font-mono text-xs text-slate-400">
                        {holding.fund_code}
                      </span>
                    </span>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={1}
                      value={Math.round((fundTargetWeights[holding.fund_code] ?? 0) * 100)}
                      onChange={(event) =>
                        handleFundTargetWeightChange(
                          holding.fund_code,
                          Number(event.target.value),
                        )
                      }
                      className="w-20 rounded-lg border border-slate-300 px-2 py-1 text-right font-mono text-sm"
                    />
                    <span className="text-sm text-slate-500">%</span>
                  </div>
                ))}
              </div>
            )}
            <p
              className={`mt-2 text-xs ${customWeightsValid ? 'text-slate-500' : 'text-rose-600'}`}
            >
              类内权重合计 {Math.round(fundWeightSum * 100)}%（需等于 100%）
            </p>
          </div>
        ) : null}

        <div>
        <h4 className="text-sm font-medium text-slate-900">规则灵敏度</h4>
        <p className="mt-1 text-sm text-slate-500">调整何时提示加减仓、合并持仓</p>

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

          <div>
            <label htmlFor="min-trade" className="block text-sm font-medium text-slate-700">
              最小建议交易额
            </label>
            <p className="text-xs text-slate-500">低于此金额的增配/减配建议将被抑制</p>
            <div className="mt-2 flex items-center gap-3">
              <input
                id="min-trade"
                type="range"
                min={0}
                max={5000}
                step={100}
                value={minSuggestedTrade}
                onChange={(event) => setMinSuggestedTrade(Number(event.target.value))}
                className="flex-1"
              />
              <span className="w-20 text-right font-mono text-sm text-slate-700">
                ¥{minSuggestedTrade}
              </span>
            </div>
          </div>

          <div>
            <label htmlFor="max-funds" className="block text-sm font-medium text-slate-700">
              大类持仓数量上限
            </label>
            <p className="text-xs text-slate-500">同大类超过此数量时提示合并为核心持仓</p>
            <div className="mt-2 flex items-center gap-3">
              <input
                id="max-funds"
                type="range"
                min={5}
                max={30}
                step={1}
                value={maxFundsPerCategory}
                onChange={(event) => setMaxFundsPerCategory(Number(event.target.value))}
                className="flex-1"
              />
              <span className="w-14 text-right font-mono text-sm text-slate-700">
                {maxFundsPerCategory} 只
              </span>
            </div>
          </div>
        </div>
        </div>

        <div>
        <h4 className="text-sm font-medium text-slate-900">基金目录</h4>
        <p className="mt-1 text-sm text-slate-500">
          搜索补代码依赖东方财富公开基金目录，建议首次使用前刷新。
        </p>
        <button
          type="button"
          onClick={handleRefreshCatalog}
          disabled={refreshingCatalog}
          className="mt-4 inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {refreshingCatalog ? '刷新中...' : '刷新基金目录'}
        </button>
        </div>
        </div>
      </details>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-lg font-medium text-slate-900">浏览器通知</h3>
        <p className="mt-1 text-sm text-slate-500">
          数据同步后若出现 strength ≥ 4 的增配/减仓信号，可收到桌面提醒（每快照一次）。
        </p>
        {!notificationsSupported() ? (
          <p className="mt-3 text-sm text-slate-500">当前浏览器不支持通知 API。</p>
        ) : (
          <div className="mt-4 space-y-4">
            <p className="text-sm text-slate-700">
              当前权限：
              <span
                className={`ml-2 rounded-full px-2 py-0.5 text-xs font-medium ${
                  notificationPermission === 'granted'
                    ? 'bg-emerald-100 text-emerald-800'
                    : notificationPermission === 'denied'
                      ? 'bg-rose-100 text-rose-800'
                      : 'bg-amber-100 text-amber-800'
                }`}
              >
                {permissionStatusLabel(notificationPermission)}
              </span>
              {notificationsEnabled ? (
                <span className="ml-2 text-xs text-slate-500">· 功能已开启</span>
              ) : null}
            </p>

            {permissionRecoveryHint(notificationPermission) ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
                {permissionRecoveryHint(notificationPermission)}
              </div>
            ) : null}

            {notificationPermission === 'granted' ? (
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                {systemNotificationVisibilityHint()}
              </div>
            ) : null}

            {notificationPreview ? (
              <div className="rounded-xl border border-slate-300 bg-white p-4 shadow-md">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  应用内预览（桌面横幅不可见时以此为准）
                </p>
                <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="font-semibold text-slate-900">{notificationPreview.title}</p>
                  <p className="mt-1 text-sm text-slate-600">{notificationPreview.body}</p>
                </div>
              </div>
            ) : null}

            <div className="flex flex-wrap items-center gap-3">
              {notificationPermission !== 'granted' ? (
                <button
                  type="button"
                  onClick={handleRequestNotificationPermission}
                  className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                >
                  授权并开启
                </button>
              ) : (
                <>
                  {!notificationsEnabled ? (
                    <button
                      type="button"
                      onClick={() => {
                        setNotificationsEnabled(true)
                        setNotificationsEnabledState(true)
                        setSuccess('已开启强信号浏览器通知')
                        setError(null)
                      }}
                      className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
                    >
                      开启通知
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleDisableNotifications}
                      className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      关闭通知
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleTestNotification}
                    className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
                  >
                    测试通知
                  </button>
                </>
              )}
            </div>

            {notificationPermission === 'default' ? (
              <p className="text-xs text-slate-500">
                点击「授权并开启」后，浏览器会弹出权限请求，请选择「允许」。若误点「阻止」，需按上方说明在站点设置中手动改回。
              </p>
            ) : null}
          </div>
        )}
      </section>

      {/* Sync History Section */}
      <section className="mt-10 border-t border-slate-200 pt-6">
        <h3 className="text-lg font-semibold text-slate-900">同步历史</h3>
        <p className="mt-1 text-sm text-slate-500">最近 3 次数据同步的执行结果</p>

        {syncLogsData && syncLogsData.logs.length > 0 ? (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-left text-slate-500">
                  <th className="px-3 py-2 font-medium">时间</th>
                  <th className="px-3 py-2 font-medium">状态</th>
                  <th className="px-3 py-2 font-medium">成功/总数</th>
                  <th className="px-3 py-2 font-medium">错误</th>
                </tr>
              </thead>
              <tbody>
                {syncLogsData.logs.map((log) => {
                  const errors: Array<{ fund_code: string; stage: string; error: string }> =
                    (() => { try { return JSON.parse(log.errors_json || '[]') } catch { return [] } })()
                  const statusDisplay: Record<string, { text: string; color: string }> = {
                    done: { text: '全部成功', color: 'text-emerald-700' },
                    partial: { text: '部分失败', color: 'text-amber-700' },
                    failed: { text: '全部失败', color: 'text-rose-700' },
                    running: { text: '进行中', color: 'text-blue-700' },
                  }
                  const display = statusDisplay[log.status] ?? { text: log.status, color: 'text-slate-700' }

                  return (
                    <tr key={log.id} className="border-b border-slate-100">
                      <td className="px-3 py-2 text-slate-700">
                        {new Date(log.started_at).toLocaleString('zh-CN')}
                      </td>
                      <td className={`px-3 py-2 font-medium ${display.color}`}>
                        {display.text}
                      </td>
                      <td className="px-3 py-2 tabular-nums text-slate-700">
                        {log.success_funds} / {log.total_funds}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {errors.length > 0
                          ? errors.map((e, i) => (
                              <span key={i} className="block text-xs">
                                {e.fund_code}: {e.error}
                              </span>
                            ))
                          : '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-500">暂无同步记录</p>
        )}
      </section>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || (isCustom && Math.abs(weightSum - 1) >= 0.01) || !customWeightsValid}
          className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {saving ? '保存中...' : '保存策略'}
        </button>
        <button
          type="button"
          onClick={handleSync}
          disabled={syncMutation.isPending}
          className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {syncMutation.isPending ? '同步中...' : '同步数据'}
        </button>
      </div>

      {llmDialog ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="llm-dialog-title"
          onClick={() => setLlmDialog(null)}
        >
          <div
            className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl"
            onClick={(event) => event.stopPropagation()}
          >
            <h4
              id="llm-dialog-title"
              className={`text-lg font-semibold ${
                llmDialog.ok ? 'text-emerald-800' : 'text-rose-800'
              }`}
            >
              {llmDialog.title}
            </h4>
            <p className="mt-3 text-sm leading-relaxed text-slate-700">{llmDialog.message}</p>
            <div className="mt-6 flex justify-end">
              <button
                type="button"
                onClick={() => setLlmDialog(null)}
                className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
              >
                知道了
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
