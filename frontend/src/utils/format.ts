const currencyFormatter = new Intl.NumberFormat('zh-CN', {
  style: 'currency',
  currency: 'CNY',
  maximumFractionDigits: 2,
})

export function formatCurrency(value: number) {
  return currencyFormatter.format(value)
}

/** Profit/loss amount: no +/- sign; direction is shown by color. */
export function formatProfitAmount(value: number) {
  return formatCurrency(Math.abs(value))
}

export function formatPercent(value: number, digits = 2) {
  return `${(value * 100).toFixed(digits)}%`
}

export function formatSignedPercent(value: number, digits = 2) {
  const formatted = formatPercent(value, digits)
  if (value > 0) return `+${formatted}`
  return formatted
}
