import { NAV_DAILY_CHANGE_THRESHOLD_PCT } from '../constants/nav'
import type { NavAnomaly } from '../types'
import { formatSignedPercent } from '../utils/format'

interface NavAnomalyBannerProps {
  anomalies: NavAnomaly[]
}

export default function NavAnomalyBanner({ anomalies }: NavAnomalyBannerProps) {
  if (anomalies.length === 0) {
    return null
  }

  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
      <h3 className="text-sm font-semibold text-amber-900">净值异动提醒</h3>
      <p className="mt-1 text-sm text-amber-800">
        以下基金最新净值日涨跌幅超过 {NAV_DAILY_CHANGE_THRESHOLD_PCT}%，可能是分红/拆分或数据源异常，请核对后再做决策。
      </p>
      <ul className="mt-3 space-y-2">
        {anomalies.map((item) => (
          <li
            key={`${item.fund_code}-${item.nav_date}`}
            className="rounded-lg border border-amber-200/80 bg-white/70 px-3 py-2 text-sm text-amber-950"
          >
            <span className="font-medium">{item.fund_name}</span>
            <span className="text-amber-700"> ({item.fund_code})</span>
            <span className="ml-2">
              {item.prev_nav_date} → {item.nav_date}：
              {formatSignedPercent(item.change_pct / 100)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
