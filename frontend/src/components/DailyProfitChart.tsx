import { useMemo } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { DailyHistoryPoint } from '../types'
import { formatProfitAmount } from '../utils/format'
import { profitLossTextClass } from '../utils/profitLoss'

interface DailyProfitChartProps {
  points: DailyHistoryPoint[]
  days: number
}

function formatAxisDate(date: string) {
  return date.slice(5)
}

export default function DailyProfitChart({ points, days }: DailyProfitChartProps) {
  const chartData = useMemo(
    () =>
      points.map((point) => ({
        date: point.date,
        label: formatAxisDate(point.date),
        daily_profit: point.daily_profit,
        complete: point.complete,
      })),
    [points],
  )

  const completePoints = useMemo(() => points.filter((point) => point.complete), [points])
  const periodTotal = useMemo(
    () => completePoints.reduce((sum, point) => sum + point.daily_profit, 0),
    [completePoints],
  )
  const canShowPeriodTotal = completePoints.length > 0

  const hasIncomplete = points.some((point) => !point.complete)

  if (chartData.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        暂无足够净值历史，同步数据并积累几个交易日后即可查看曲线。
      </p>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm text-slate-600">
          近 {days} 个交易日合计：
          {canShowPeriodTotal ? (
            <span className={`ml-1 font-semibold tabular-nums ${profitLossTextClass(periodTotal)}`}>
              {formatProfitAmount(periodTotal)}
            </span>
          ) : (
            <span className="ml-1 text-slate-400">—</span>
          )}
        </p>
        {hasIncomplete ? (
          <p className="text-xs text-amber-700">部分日期因缺净值未计入组合完整日盈亏</p>
        ) : null}
      </div>

      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={false}
              tickLine={false}
              minTickGap={24}
            />
            <YAxis
              tick={{ fontSize: 11, fill: '#64748b' }}
              axisLine={false}
              tickLine={false}
              width={72}
              tickFormatter={(value) => formatProfitAmount(value)}
            />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <Tooltip
              formatter={(value) => [
                formatProfitAmount(Number(value ?? 0)),
                '日盈亏',
              ]}
              labelFormatter={(_, payload) => {
                const row = payload?.[0]?.payload as { date?: string } | undefined
                return row?.date ?? ''
              }}
              contentStyle={{
                borderRadius: '0.5rem',
                borderColor: '#e2e8f0',
                fontSize: '12px',
              }}
            />
            <Line
              type="monotone"
              dataKey="daily_profit"
              stroke="#6366f1"
              strokeWidth={2}
              dot={{ r: 2, fill: '#6366f1' }}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
