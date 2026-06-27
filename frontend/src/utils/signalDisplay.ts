import type { Signal } from '../types'

export const SIGNAL_TYPE_LABELS: Record<string, string> = {
  reduce: '减仓',
  add: '增配',
  hold: '持有',
  watch: '观察',
}

export const SIGNAL_TYPE_STYLES: Record<string, string> = {
  reduce: 'bg-rose-100 text-rose-800',
  add: 'bg-emerald-100 text-emerald-800',
  hold: 'bg-slate-100 text-slate-700',
  watch: 'bg-amber-100 text-amber-800',
}

export function signalTitle(signal: Signal) {
  if (signal.fund_code) {
    return signal.fund_name ?? signal.fund_code
  }
  return signal.category_label ?? signal.category ?? '大类配置'
}

export function formatSignalScore(value: number) {
  const prefix = value > 0 ? '+' : ''
  return `${prefix}${value.toFixed(1)}`
}

export function formatSignalAmount(value: number) {
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    maximumFractionDigits: 0,
  }).format(Math.abs(value))
}

export function scoreTextClass(score: number) {
  if (score > 0) return 'text-emerald-600'
  if (score < 0) return 'text-rose-600'
  return 'text-slate-600'
}

export const REASON_RULE_LABELS: Record<string, string> = {
  add: '增配',
  reduce: '减配',
  category_underweight: '大类低配',
  category_overweight: '大类超配',
  single_fund_concentration: '集中度',
  high_correlation: '高相关',
  no_action: '无需调整',
  excess_return_1y: '超额收益',
  sharpe_1y: '夏普比率',
  max_drawdown_1y: '最大回撤',
  purchase_limit_blocked: '限购受阻',
  purchase_suspended: '暂停申购',
  redemption_hard_to_rebuy: '卖出难买回',
  performance_blocked_add: '业绩过滤',
  performance_prioritized_reduce: '减配优先',
  category_overcrowded: '持仓过多',
  below_min_trade: '低于最小交易额',
}

export function formatReasonRule(rule: string) {
  return REASON_RULE_LABELS[rule] ?? rule
}

export function formatFundLabel(code: string, name?: string | null) {
  if (name) return `${name}（${code}）`
  return code
}

const CORRELATION_VALUE = /相关系数\s+([\d.]+)/
const FUND_CODE = /\d{6}/g

export function resolveCorrelationPair(
  reason: { detail: string; paired_fund_code?: string | null; paired_fund_name?: string | null; correlation?: number | null },
  selfCode: string,
  nameByCode?: Record<string, string | null | undefined>,
) {
  let pairedCode = reason.paired_fund_code ?? null
  let correlation = reason.correlation ?? null
  const detail = reason.detail ?? ''

  if (correlation == null) {
    const match = detail.match(CORRELATION_VALUE)
    if (match) correlation = Number.parseFloat(match[1])
  }

  if (!pairedCode) {
    const codes = detail.match(FUND_CODE) ?? []
    pairedCode = codes.find((code) => code !== selfCode) ?? null
  }

  let pairedName = reason.paired_fund_name ?? null
  if (!pairedName && pairedCode && nameByCode) {
    pairedName = nameByCode[pairedCode] ?? null
  }

  return { pairedCode, pairedName, correlation }
}

/** Action type for filtering — aligns weak rebalance hints with 增配/减仓 tabs. */
export function signalActionType(signal: Signal): string {
  const protectedByPurchaseLimit = signal.reasons.some(
    (reason) =>
      reason.layer === 'purchase_limit' &&
      (reason.rule === 'redemption_hard_to_rebuy' ||
        reason.rule === 'purchase_limit_blocked' ||
        reason.rule === 'purchase_suspended'),
  )
  if (protectedByPurchaseLimit) {
    return 'watch'
  }

  if (signal.signal_type !== 'hold') {
    return signal.signal_type
  }

  const rebalanceRules = new Set(signal.reasons.filter((r) => r.layer === 'rebalance').map((r) => r.rule))
  if (
    signal.suggested_amount > 0 &&
    signal.score > 0 &&
    (rebalanceRules.has('add') || rebalanceRules.has('category_underweight'))
  ) {
    const blockedByLimit = signal.reasons.some(
      (reason) =>
        reason.layer === 'purchase_limit' &&
        (reason.rule === 'purchase_limit_blocked' || reason.rule === 'purchase_suspended'),
    )
    return blockedByLimit ? 'watch' : 'add'
  }
  if (
    signal.suggested_amount < 0 &&
    signal.score < 0 &&
    (rebalanceRules.has('reduce') || rebalanceRules.has('category_overweight'))
  ) {
    return 'reduce'
  }
  return signal.signal_type
}

export function summarizeReasons(signal: Signal, maxLength = 48) {
  if (signal.reasons.length === 0) return '—'
  const first = signal.reasons[0]
  const text = `${formatReasonRule(first.rule)} · ${first.detail}`
  if (text.length <= maxLength) return text
  return `${text.slice(0, maxLength)}…`
}
