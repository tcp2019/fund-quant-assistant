export interface Holding {
  fund_code: string
  fund_name: string
  shares: number
  cost_price: number
  market_value: number
  profit: number
  profit_rate: number
  platform: string
  hold_days: number | null
  weight_pct: number
}

export interface Overview {
  snapshot_id: number | null
  total_value: number
  total_cost: number
  total_profit: number
  total_profit_rate: number
  holdings: Holding[]
}

export type OcrPlatform = 'alipay' | 'tiantian' | 'licaitong'

export interface ParsedHolding {
  fund_code: string
  fund_name: string
  shares: number
  cost_price: number
  market_value: number
  profit: number
  profit_rate: number
  platform: string
  confidence?: number
}

export interface OcrUploadResponse {
  job_id: number
  holdings: ParsedHolding[]
  warnings: string[]
}

export interface OcrConfirmResponse {
  snapshot_id: number
}

export interface SignalReason {
  layer: string
  rule: string
  detail: string
  category?: string | null
  category_label?: string | null
}

export interface Signal {
  id: number
  snapshot_id: number
  fund_code: string
  fund_name: string | null
  category: string | null
  category_label: string | null
  signal_type: 'reduce' | 'add' | 'hold' | 'watch' | string
  score: number
  strength: number
  reasons: SignalReason[]
  suggested_amount: number
  created_at: string
}

export interface SignalsListOut {
  snapshot_id: number | null
  signals: Signal[]
}

export interface CorrelationOut {
  snapshot_id: number | null
  labels: string[]
  matrix: number[][]
  period_days: number
}

export interface RiskOut {
  snapshot_id: number | null
  volatility: number | null
  sharpe: number | null
  max_dd: number | null
  period_days: number
}
