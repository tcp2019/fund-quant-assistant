import { useState } from 'react'
import { fetchThemeCandidates } from '../api/client'
import type { ThemeAllocation, ThemeCandidatesOut } from '../types'
import AllocationChart from './AllocationChart'

interface ThemeExposurePanelProps {
  allocation: ThemeAllocation[]
}

function formatReturn(candidate: ThemeCandidatesOut['candidates'][number]) {
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

export default function ThemeExposurePanel({ allocation }: ThemeExposurePanelProps) {
  const [loadingTheme, setLoadingTheme] = useState<string | null>(null)
  const [candidatesByTheme, setCandidatesByTheme] = useState<Record<string, ThemeCandidatesOut>>(
    {},
  )
  const [error, setError] = useState<string | null>(null)

  async function loadCandidates(themeId: string) {
    setLoadingTheme(themeId)
    setError(null)
    try {
      const data = await fetchThemeCandidates(themeId, 'return_1m', 3)
      setCandidatesByTheme((current) => ({ ...current, [themeId]: data }))
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载候选失败')
    } finally {
      setLoadingTheme(null)
    }
  }

  if (allocation.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        暂无主题暴露。导入含「半导体/CPO/通信」等关键词的基金，同步后会自动识别。
      </p>
    )
  }

  return (
    <div className="space-y-4">
      <AllocationChart allocation={allocation} emptyText="暂无主题配置数据" showLegend={false} />
      <div className="space-y-3">
        {allocation.map((item) => {
          const candidates = candidatesByTheme[item.theme]
          return (
            <div
              key={item.theme}
              className="rounded-lg border border-slate-200 bg-slate-50/60 px-4 py-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-900">{item.label}</p>
                  <p className="text-xs text-slate-500">
                    占组合 {item.weight_pct.toFixed(2)}% · ¥
                    {item.market_value.toLocaleString('zh-CN')}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void loadCandidates(item.theme)}
                  disabled={loadingTheme === item.theme}
                  className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-60"
                >
                  {loadingTheme === item.theme ? '加载中...' : '近1月热点候选'}
                </button>
              </div>
              {candidates && candidates.candidates.length > 0 ? (
                <ul className="mt-3 divide-y divide-slate-200 overflow-hidden rounded-md border border-slate-200 bg-white">
                  {candidates.candidates.map((candidate) => (
                    <li
                      key={candidate.fund_code}
                      className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
                    >
                      <div>
                        <p className="font-medium text-slate-900">{candidate.fund_name}</p>
                        <p className="text-xs text-slate-500">{candidate.fund_code}</p>
                      </div>
                      <span className="font-medium tabular-nums text-slate-900">
                        {formatReturn(candidate)}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          )
        })}
      </div>
      {error ? <p className="text-sm text-rose-600">{error}</p> : null}
      <p className="text-xs text-slate-500">
        主题按基金名称关键词识别；候选按近1月收益排序，仅供参考。
      </p>
    </div>
  )
}
