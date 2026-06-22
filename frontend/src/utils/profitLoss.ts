/** A-share convention: up/profit = red, down/loss = green */
export function profitLossTextClass(value: number, zeroClass = 'text-slate-600'): string {
  if (value > 0) return 'text-rose-600'
  if (value < 0) return 'text-emerald-600'
  return zeroClass
}

export function profitLossToneClass(
  tone: 'profit' | 'loss' | 'default',
  defaultClass = 'text-slate-900',
): string {
  if (tone === 'profit') return 'text-rose-600'
  if (tone === 'loss') return 'text-emerald-600'
  return defaultClass
}
