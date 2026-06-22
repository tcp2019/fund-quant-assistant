export interface HoldingTheme {
  theme: string
  label: string
}

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
  themes?: HoldingTheme[]
}

export interface Overview {
  snapshot_id: number | null
  total_value: number
  total_cost: number
  total_profit: number
  total_profit_rate: number
  holdings: Holding[]
  category_allocation: CategoryAllocation[]
  theme_allocation?: ThemeAllocation[]
  top_holdings: Holding[]
  concentration_top5_pct: number
  data_as_of_date?: string | null
}

export interface CategoryAllocation {
  category: string
  label: string
  weight_pct: number
  market_value: number
}

export interface ThemeAllocation {
  theme: string
  label: string
  weight_pct: number
  market_value: number
}

export interface SnapshotSummary {
  id: number
  created_at: string
  source: string
  total_value: number
}

export interface SnapshotsListOut {
  snapshots: SnapshotSummary[]
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
  warnings?: string[]
}

export interface OcrUploadResponse {
  job_id: number
  holdings: ParsedHolding[]
  warnings: string[]
}

export interface OcrConfirmResponse {
  snapshot_id: number
}

export interface FundSearchResult {
  fund_code: string
  fund_name: string
  fund_type: string
}

export interface FundSearchOut {
  results: FundSearchResult[]
  catalog_ready: boolean
}

export interface FundCandidate {
  fund_code: string
  fund_name: string
  category: string
  return_1y: number | null
  return_1m: number | null
  return_1w: number | null
  as_of_date: string
  data_source: string
}

export interface ThemeCandidatesOut {
  theme: string
  label: string
  sort_by: string
  candidates: FundCandidate[]
}

export interface ThemeOption {
  theme: string
  label: string
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
  candidates?: FundCandidate[]
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

export interface StrategyConfig {
  template_name: string
  target_weights: Record<string, number>
  thresholds: {
    rebalance_deviation_pct: number
    rebalance_force_days: number
    single_fund_max_pct: number
    correlation_max: number
  }
  intra_category_mode: 'equal' | 'pro_rata' | 'custom'
  fund_target_weights: Record<string, number>
}

export interface DataSyncResult {
  synced: number
  codes: string[]
  details: Array<{
    code: string
    nav_rows?: number
    status: string
    error?: string
  }>
  signals_count?: number
  revalued?: number
  as_of_date?: string | null
}
