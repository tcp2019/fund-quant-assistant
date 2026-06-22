import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { chartColor } from '../utils/chartColors'

interface AllocationChartProps {
  allocation: Array<{ label: string; weight_pct: number; market_value: number }>
  emptyText?: string
  showLegend?: boolean
}

export default function AllocationChart({
  allocation,
  emptyText = '暂无配置数据',
  showLegend = true,
}: AllocationChartProps) {
  if (allocation.length === 0) {
    return <p className="text-sm text-slate-500">{emptyText}</p>
  }

  const chartData = allocation.map((item) => ({
    name: item.label,
    value: item.weight_pct,
    marketValue: item.market_value,
  }))

  return (
    <div className="space-y-2">
      <div className="h-56">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={52}
              outerRadius={84}
              paddingAngle={2}
            >
              {chartData.map((entry, index) => (
                <Cell key={entry.name} fill={chartColor(index)} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value, _name, item) => {
                const pct = typeof value === 'number' ? value : Number(value ?? 0)
                const payload = item?.payload as { name?: string; marketValue?: number } | undefined
                return [
                  `${pct.toFixed(2)}% · ¥${(payload?.marketValue ?? 0).toLocaleString('zh-CN')}`,
                  payload?.name ?? '',
                ]
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      {showLegend ? (
        <ul className="grid gap-2 sm:grid-cols-2">
          {allocation.map((item, index) => (
            <li key={`${item.label}-${index}`} className="flex items-center gap-2 text-sm">
              <span
                className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: chartColor(index) }}
              />
              <span className="flex-1 text-slate-700">{item.label}</span>
              <span className="font-semibold tabular-nums text-slate-900">
                {item.weight_pct.toFixed(2)}%
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
