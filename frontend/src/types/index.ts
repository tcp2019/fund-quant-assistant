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
  current_value?: number
  current_profit?: number
  nav_date?: string | null
  themes?: HoldingTheme[]
}

export interface Overview {
  snapshot_id: number | null
  total_value: number
  total_cost: number
  total_profit: number
  total_profit_rate: number
  current_total_value?: number
  current_total_profit?: number
  current_total_profit_rate?: number
  nav_date?: string | null
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
  paired_fund_code?: string | null
  paired_fund_name?: string | null
  correlation?: number | null
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
  interpretation?: string | null
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
    min_suggested_trade_cny: number
    max_funds_per_category: number
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

export interface ActionItem {
  action: 'sell' | 'add_holding' | 'explore'
  fund_code: string
  fund_name: string | null
  category: string | null
  category_label: string | null
  suggested_amount: number
  score: number
  strength: number
  reason_summary: string
  signal_id: number | null
  candidates: FundCandidate[]
}

export interface HotTheme {
  theme: string
  label: string
  heat_score: number
  return_1m_median: number | null
  portfolio_weight_pct: number
  aligned_gap: boolean
  aligned_category_label: string | null
  candidates: FundCandidate[]
}

export interface StructuralAction {
  action: 'consolidate' | 'rebalance_review'
  category: string
  category_label: string
  detail: string
  fund_count?: number | null
  blocked_buy_count?: number | null
}

export interface OpportunitiesOut {
  snapshot_id: number | null
  data_as_of_date: string | null
  structural_actions: StructuralAction[]
  sell_actions: ActionItem[]
  buy_actions: ActionItem[]
  explore_actions: ActionItem[]
  hot_themes: HotTheme[]
}

export interface SensitivitySignal {
  category: string
  signal_type: string
  deviation_pct: number
  suggested_amount: number
}

export interface SensitivityScenario {
  threshold_pct: number
  triggered_categories: number
  signals: SensitivitySignal[]
}

export interface SensitivityReport {
  snapshot_id: number | null
  total_value: number
  scenarios: SensitivityScenario[]
}

export interface SnapshotStat {
  snapshot_id: number
  created_at: string
  rebalance_triggers: number
  category_count_max: number
}

export interface SnapshotStatsOut {
  snapshots: SnapshotStat[]
}

export interface SyncLogEntry {
  id: number
  started_at: string
  finished_at: string | null
  status: 'running' | 'done' | 'partial' | 'failed'
  total_funds: number
  success_funds: number
  failed_funds: number
  errors_json: string
}

export interface StyleExposure {
  size_exposure: Record<string, number>
  style_exposure: Record<string, number>
  snapshot_id: number | null
}

export interface MacroIndicators {
  bond_10y: number | null
  bond_10y_trend: string
  shibor_overnight: number | null
  environment: string
  available: boolean
}

export interface BacktestResult {
  snapshots_tested: number
  signals_generated: number
  hit_rate: number | null
  avg_excess_return: number | null
  detail: string
}
