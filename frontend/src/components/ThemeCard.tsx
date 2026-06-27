import type { FundCandidate, HotTheme } from '../types'

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

export default function ThemeCard({ theme }: { theme: HotTheme }) {
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
