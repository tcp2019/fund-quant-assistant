import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { confirmOcr, fetchSignals, syncData, uploadOcr } from '../api/client'
import { queryKeys } from '../api/queries'
import FundSearchCombobox from '../components/FundSearchCombobox'
import type { FundSearchResult, OcrPlatform, ParsedHolding } from '../types'
import { maybeNotifyStrongSignals, summarizeStrongSignals } from '../utils/notifications'

const PLATFORMS: { value: OcrPlatform; label: string }[] = [
  { value: 'alipay', label: '支付宝' },
  { value: 'tiantian', label: '天天基金' },
  { value: 'licaitong', label: '腾讯理财通' },
]

type EditableFieldKey = keyof ParsedHolding

const EDITABLE_FIELDS: {
  key: EditableFieldKey
  label: string
  type: 'text' | 'number' | 'percent'
}[] = [
  { key: 'fund_code', label: '基金代码', type: 'text' },
  { key: 'fund_name', label: '基金名称', type: 'text' },
  { key: 'shares', label: '份额', type: 'number' },
  { key: 'cost_price', label: '成本价', type: 'number' },
  { key: 'market_value', label: '市值', type: 'number' },
  { key: 'profit', label: '盈亏', type: 'number' },
  { key: 'profit_rate', label: '收益率 (%)', type: 'percent' },
]

function displayFieldValue(holding: ParsedHolding, key: EditableFieldKey): string {
  if (key === 'profit_rate') {
    return holding.profit_rate === 0 ? '' : String(Number((holding.profit_rate * 100).toFixed(4)))
  }
  const value = holding[key]
  return value === undefined || value === null ? '' : String(value)
}

function updateHoldingField(
  holdings: ParsedHolding[],
  index: number,
  key: EditableFieldKey,
  rawValue: string,
): ParsedHolding[] {
  return holdings.map((holding, rowIndex) => {
    if (rowIndex !== index) {
      return holding
    }

    if (key === 'fund_code' || key === 'fund_name' || key === 'platform') {
      return { ...holding, [key]: rawValue }
    }

    if (key === 'profit_rate') {
      const parsed = rawValue === '' ? 0 : Number(rawValue)
      return {
        ...holding,
        profit_rate: Number.isFinite(parsed) ? parsed / 100 : holding.profit_rate,
      }
    }

    const parsed = rawValue === '' ? 0 : Number(rawValue)
    return { ...holding, [key]: Number.isFinite(parsed) ? parsed : holding[key] }
  })
}

function rowNeedsAttention(holding: ParsedHolding): boolean {
  return !holding.fund_code || (holding.warnings?.length ?? 0) > 0
}

function holdingsForConfirm(holdings: ParsedHolding[]): ParsedHolding[] {
  return holdings.map(({ warnings: _warnings, confidence: _confidence, ...holding }) => holding)
}

export default function ImportPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const uploadMutation = useMutation({ mutationFn: uploadOcr })
  const confirmMutation = useMutation({
    mutationFn: ({ jobId, holdings }: { jobId: number; holdings: any }) =>
      confirmOcr(jobId, holdings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.overview })
      queryClient.invalidateQueries({ queryKey: queryKeys.holdings })
    },
  })

  const [platform, setPlatform] = useState<OcrPlatform>('alipay')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [jobId, setJobId] = useState<number | null>(null)
  const [holdings, setHoldings] = useState<ParsedHolding[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [syncing, setSyncing] = useState(false)
  const [importedSnapshotId, setImportedSnapshotId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  function resetImportFlow() {
    setJobId(null)
    setHoldings([])
    setWarnings([])
    setImportedSnapshotId(null)
    setError(null)
  }

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    resetImportFlow()

    if (!file && !text.trim()) {
      setError('请粘贴 OCR 文本，或选择一张持仓截图。')
      return
    }

    try {
      const result = await uploadMutation.mutateAsync({
        platform,
        text: text.trim(),
        file,
      })
      setJobId(result.job_id)
      setHoldings(result.holdings)
      setWarnings(result.warnings)
      if (result.holdings.length === 0) {
        setError(
          '未能从文本中解析出持仓记录。请确认已选择正确来源平台，或检查粘贴内容是否为支付宝/天天基金/理财通 OCR 文本。',
        )
      }
    } catch (err) {
      resetImportFlow()
      setError(err instanceof Error ? err.message : '解析失败')
    }
  }

  async function handleConfirm() {
    if (jobId === null) {
      return
    }

    if (holdings.length === 0) {
      setError('没有可确认的持仓记录，请先解析截图或文本。')
      return
    }

    setError(null)
    try {
      const result = await confirmMutation.mutateAsync({
        jobId,
        holdings: holdingsForConfirm(holdings),
      })
      setImportedSnapshotId(result.snapshot_id)
      setHoldings([])
      setWarnings([])
    } catch (err) {
      setError(err instanceof Error ? err.message : '确认导入失败')
    }
  }

  async function handleSyncAndViewSignals() {
    setSyncing(true)
    setError(null)
    try {
      await syncData()
      const signalData = await fetchSignals()
      const summary = summarizeStrongSignals(signalData.snapshot_id, signalData.signals)
      if (summary) {
        maybeNotifyStrongSignals(summary)
      }
      navigate('/advice')
    } catch (err) {
      setError(err instanceof Error ? err.message : '同步失败')
    } finally {
      setSyncing(false)
    }
  }

  function applyFundSearch(index: number, result: FundSearchResult) {
    setHoldings((current) =>
      current.map((holding, rowIndex) =>
        rowIndex === index
          ? { ...holding, fund_code: result.fund_code, fund_name: result.fund_name }
          : holding,
      ),
    )
  }

  function removeHolding(index: number) {
    setHoldings((current) => current.filter((_, rowIndex) => rowIndex !== index))
  }

  if (importedSnapshotId !== null) {
    return (
      <div className="space-y-6">
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-8 text-center">
          <h2 className="text-xl font-semibold text-emerald-900">导入成功</h2>
          <p className="mt-2 text-sm text-emerald-800">
            已创建快照 #{importedSnapshotId}。同步净值数据后即可生成量化信号。
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              onClick={handleSyncAndViewSignals}
              disabled={syncing}
              className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
            >
              {syncing ? '同步中...' : '同步数据并查看信号'}
            </button>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              查看总览
            </button>
          </div>
          {error ? (
            <div className="mx-auto mt-4 max-w-lg rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </div>
      </div>
    )
  }

  const displayError =
    error ||
    (uploadMutation.error instanceof Error ? uploadMutation.error.message : null) ||
    (confirmMutation.error instanceof Error ? confirmMutation.error.message : null)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">导入持仓</h2>
        <p className="mt-1 text-sm text-slate-500">
          粘贴 OCR 文本或上传截图，确认解析结果后写入最新快照。
        </p>
      </div>

      <form
        onSubmit={handleUpload}
        className="space-y-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
      >
        <div>
          <label htmlFor="platform" className="block text-sm font-medium text-slate-700">
            来源平台
          </label>
          <select
            id="platform"
            value={platform}
            onChange={(event) => setPlatform(event.target.value as OcrPlatform)}
            className="mt-2 w-full max-w-xs rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          >
            {PLATFORMS.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="ocr-text" className="block text-sm font-medium text-slate-700">
            OCR 文本
          </label>
          <p className="mt-1 text-xs text-slate-500">v1 推荐流程：将截图 OCR 结果粘贴到下方。</p>
          <textarea
            id="ocr-text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={10}
            placeholder="粘贴支付宝 / 天天基金 / 理财通持仓 OCR 文本..."
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 shadow-sm focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
          />
        </div>

        <div>
          <label htmlFor="ocr-file" className="block text-sm font-medium text-slate-700">
            截图上传（可选）
          </label>
          <p className="mt-1 text-xs text-slate-500">
            若已选择图片，将优先走图片 OCR；否则使用上方文本。
          </p>
          <input
            id="ocr-file"
            type="file"
            accept="image/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-2 block w-full text-sm text-slate-600 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-200"
          />
        </div>

        {displayError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {displayError}
          </div>
        )}

        <button
          type="submit"
          disabled={uploadMutation.isPending}
          className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {uploadMutation.isPending ? '解析中...' : '解析持仓'}
        </button>
      </form>

      {warnings.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-5">
          <h3 className="text-sm font-semibold text-amber-900">解析警告</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-800">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      {holdings.length > 0 && (
        <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-semibold text-slate-900">解析结果</h3>
              <p className="mt-1 text-sm text-slate-500">
                共 {holdings.length} 条记录，可在确认前直接编辑。缺代码或带警告的行已高亮。
              </p>
            </div>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={confirmMutation.isPending}
              className="inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-emerald-300"
            >
              {confirmMutation.isPending ? '导入中...' : '确认导入'}
            </button>
          </div>

          {displayError ? (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {displayError}
            </div>
          ) : null}

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  {EDITABLE_FIELDS.map(({ label }) => (
                    <th key={label} className="px-3 py-3 font-medium">
                      {label}
                    </th>
                  ))}
                  <th className="px-3 py-3 font-medium">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {holdings.map((holding, index) => {
                  const needsAttention = rowNeedsAttention(holding)
                  return (
                    <tr
                      key={`${holding.fund_code}-${holding.fund_name}-${index}`}
                      className={needsAttention ? 'bg-amber-50/80' : undefined}
                    >
                      {EDITABLE_FIELDS.map(({ key, type }) => (
                        <td key={key} className="px-3 py-2 align-top">
                          <input
                            type={type === 'percent' ? 'number' : type}
                            step={type === 'percent' ? '0.01' : type === 'number' ? 'any' : undefined}
                            value={displayFieldValue(holding, key)}
                            onChange={(event) =>
                              setHoldings((current) =>
                                updateHoldingField(current, index, key, event.target.value),
                              )
                            }
                            className="w-full min-w-[7rem] rounded-md border border-slate-300 px-2 py-1.5 text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                          />
                          {key === 'fund_code' && !holding.fund_code ? (
                            <div className="mt-2">
                              <FundSearchCombobox onSelect={(result) => applyFundSearch(index, result)} />
                            </div>
                          ) : null}
                          {key === 'fund_code' && (holding.warnings?.length ?? 0) > 0 ? (
                            <ul className="mt-1 space-y-0.5 text-xs text-amber-700">
                              {holding.warnings?.map((warning) => (
                                <li key={warning}>{warning}</li>
                              ))}
                            </ul>
                          ) : null}
                        </td>
                      ))}
                      <td className="px-3 py-2 align-top">
                        <button
                          type="button"
                          onClick={() => removeHolding(index)}
                          className="rounded-md border border-slate-300 px-2 py-1 text-xs text-slate-600 hover:bg-slate-50"
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
