import { Link } from 'react-router-dom'
import type { HotTheme } from '../types'
import { profitLossTextClass } from '../utils/profitLoss'

interface HotThemeRadarProps {
  themes: HotTheme[]
}

export default function HotThemeRadar({ themes }: HotThemeRadarProps) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-base font-semibold text-slate-900">热点雷达</h3>
          <p className="mt-1 text-sm text-slate-500">主题基金近 1 月收益中位数排行</p>
        </div>
        <Link
          to="/opportunities?tab=themes"
          className="text-sm font-medium text-slate-700 hover:text-slate-900"
        >
          查看全部 →
        </Link>
      </div>

      {themes.length === 0 ? (
        <p className="rounded-xl border border-slate-200 bg-white px-5 py-4 text-sm text-slate-500 shadow-sm">
          热点数据暂不可用，请稍后同步
        </p>
      ) : (
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <div className="flex gap-3">
            {themes.map((theme) => (
              <Link
                key={theme.theme}
                to="/opportunities?tab=themes"
                className="flex min-w-[200px] shrink-0 flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-colors hover:border-slate-300 hover:bg-slate-50"
              >
                <p className="font-medium text-slate-900">{theme.label}</p>
                <div className="mt-2 space-y-1 text-sm">
                  {theme.return_1m_median !== null ? (
                    <p
                      className={`tabular-nums ${profitLossTextClass(theme.return_1m_median)}`}
                    >
                      近1月 {theme.return_1m_median.toFixed(2)}%
                    </p>
                  ) : (
                    <p className="text-slate-500">近1月 —</p>
                  )}
                  <p className="tabular-nums text-slate-600">
                    组合 {theme.portfolio_weight_pct.toFixed(2)}%
                  </p>
                </div>
                {theme.aligned_gap && theme.aligned_category_label ? (
                  <span className="mt-3 inline-flex self-start rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">
                    与{theme.aligned_category_label}低配一致
                  </span>
                ) : null}
              </Link>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-slate-500">
        热点按主题基金近 1 月收益中位数排序，反映近期业绩而非新闻舆情，仅供参考，不构成投资建议。
      </p>
    </section>
  )
}
