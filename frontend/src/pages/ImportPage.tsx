import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { confirmOcr, uploadOcr } from '../api/client'
import type { OcrPlatform, ParsedHolding } from '../types'

const PLATFORMS: { value: OcrPlatform; label: string }[] = [
  { value: 'alipay', label: '支付宝' },
  { value: 'tiantian', label: '天天基金' },
  { value: 'licaitong', label: '腾讯理财通' },
]

const EDITABLE_FIELDS: {
  key: keyof ParsedHolding
  label: string
  type: 'text' | 'number'
}[] = [
  { key: 'fund_code', label: '基金代码', type: 'text' },
  { key: 'fund_name', label: '基金名称', type: 'text' },
  { key: 'shares', label: '份额', type: 'number' },
  { key: 'cost_price', label: '成本价', type: 'number' },
  { key: 'market_value', label: '市值', type: 'number' },
  { key: 'profit', label: '盈亏', type: 'number' },
  { key: 'profit_rate', label: '收益率', type: 'number' },
]

function updateHoldingField(
  holdings: ParsedHolding[],
  index: number,
  key: keyof ParsedHolding,
  rawValue: string,
): ParsedHolding[] {
  return holdings.map((holding, rowIndex) => {
    if (rowIndex !== index) {
      return holding
    }

    if (key === 'fund_code' || key === 'fund_name' || key === 'platform') {
      return { ...holding, [key]: rawValue }
    }

    const parsed = rawValue === '' ? 0 : Number(rawValue)
    return { ...holding, [key]: Number.isFinite(parsed) ? parsed : holding[key] }
  })
}

export default function ImportPage() {
  const navigate = useNavigate()
  const [platform, setPlatform] = useState<OcrPlatform>('alipay')
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [jobId, setJobId] = useState<number | null>(null)
  const [holdings, setHoldings] = useState<ParsedHolding[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [uploading, setUploading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault()
    setError(null)

    if (!file && !text.trim()) {
      setError('请粘贴 OCR 文本，或选择一张持仓截图。')
      return
    }

    setUploading(true)
    try {
      const result = await uploadOcr({
        platform,
        text: text.trim(),
        file,
      })
      setJobId(result.job_id)
      setHoldings(result.holdings)
      setWarnings(result.warnings)
    } catch (err) {
      setJobId(null)
      setHoldings([])
      setWarnings([])
      setError(err instanceof Error ? err.message : '解析失败')
    } finally {
      setUploading(false)
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

    setConfirming(true)
    setError(null)
    try {
      await confirmOcr(jobId, holdings)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : '确认导入失败')
    } finally {
      setConfirming(false)
    }
  }

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

        {error && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={uploading}
          className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
        >
          {uploading ? '解析中...' : '解析持仓'}
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
                共 {holdings.length} 条记录，可在确认前直接编辑。
              </p>
            </div>
            <button
              type="button"
              onClick={handleConfirm}
              disabled={confirming}
              className="inline-flex rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-emerald-300"
            >
              {confirming ? '导入中...' : '确认导入'}
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-sm">
              <thead className="bg-slate-50 text-left text-slate-500">
                <tr>
                  {EDITABLE_FIELDS.map(({ label }) => (
                    <th key={label} className="px-3 py-3 font-medium">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {holdings.map((holding, index) => (
                  <tr key={`${holding.fund_code}-${index}`}>
                    {EDITABLE_FIELDS.map(({ key, type }) => (
                      <td key={key} className="px-3 py-2">
                        <input
                          type={type}
                          value={String(holding[key] ?? '')}
                          onChange={(event) =>
                            setHoldings((current) =>
                              updateHoldingField(current, index, key, event.target.value),
                            )
                          }
                          className="w-full min-w-[7rem] rounded-md border border-slate-300 px-2 py-1.5 text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                        />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
