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
