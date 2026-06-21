interface StatCardProps {
  title: string
  value: string
  subtitle?: string
  tone?: 'default' | 'profit' | 'loss'
}

export default function StatCard({
  title,
  value,
  subtitle,
  tone = 'default',
}: StatCardProps) {
  const valueClass =
    tone === 'profit'
      ? 'text-emerald-600'
      : tone === 'loss'
        ? 'text-rose-600'
        : 'text-slate-900'

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{title}</p>
      <p className={`mt-2 text-2xl font-semibold tracking-tight ${valueClass}`}>
        {value}
      </p>
      {subtitle ? <p className="mt-1 text-sm text-slate-500">{subtitle}</p> : null}
    </div>
  )
}
