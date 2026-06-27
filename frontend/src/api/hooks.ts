import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchBacktestSensitivity,
  fetchBacktestSnapshotStats,
  fetchCorrelation,
  fetchHoldings,
  fetchHotThemes,
  fetchMacroIndicators,
  fetchOpportunities,
  fetchOverview,
  fetchRisk,
  fetchSignals,
  fetchSnapshots,
  fetchStrategy,
  fetchStyleExposure,
  fetchSyncLogs,
  queryKeys,
  syncData,
  updateStrategy,
} from './queries'
import type { StrategyConfig } from '../types'

// ── Queries ──

export function useOverview() {
  return useQuery({ queryKey: queryKeys.overview, queryFn: fetchOverview })
}

export function useHoldings() {
  return useQuery({ queryKey: queryKeys.holdings, queryFn: fetchHoldings })
}

export function useSnapshots() {
  return useQuery({ queryKey: queryKeys.snapshots, queryFn: fetchSnapshots })
}

export function useSignals() {
  return useQuery({ queryKey: queryKeys.signals, queryFn: fetchSignals })
}

export function useCorrelation() {
  return useQuery({ queryKey: queryKeys.correlation, queryFn: fetchCorrelation })
}

export function useRisk() {
  return useQuery({ queryKey: queryKeys.risk, queryFn: fetchRisk })
}

export function useStrategy() {
  return useQuery({ queryKey: queryKeys.strategy, queryFn: fetchStrategy })
}

export function useOpportunities(params?: {
  sell_limit?: number
  buy_limit?: number
  explore_limit?: number
  theme_limit?: number
  include_hot_themes?: boolean
  include_theme_candidates?: boolean
}) {
  return useQuery({
    queryKey: queryKeys.opportunities(params),
    queryFn: () => fetchOpportunities(params),
  })
}

export function useHotThemes(params?: {
  theme_limit?: number
  include_candidates?: boolean
}) {
  return useQuery({
    queryKey: queryKeys.hotThemes(params),
    queryFn: () => fetchHotThemes(params),
  })
}

export function useBacktestSensitivity() {
  return useQuery({
    queryKey: queryKeys.backtestSensitivity,
    queryFn: fetchBacktestSensitivity,
  })
}

export function useBacktestSnapshotStats() {
  return useQuery({
    queryKey: queryKeys.backtestSnapshotStats,
    queryFn: fetchBacktestSnapshotStats,
  })
}

export function useSyncLogs(limit = 3) {
  return useQuery({
    queryKey: queryKeys.syncLogs,
    queryFn: () => fetchSyncLogs(limit),
  })
}

export function useStyleExposure() {
  return useQuery({ queryKey: queryKeys.styleExposure, queryFn: fetchStyleExposure })
}

export function useMacroIndicators() {
  return useQuery({ queryKey: queryKeys.macro, queryFn: fetchMacroIndicators })
}

// ── Mutations ──

export function useSyncData() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: syncData,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.signals })
      queryClient.invalidateQueries({ queryKey: queryKeys.overview })
      queryClient.invalidateQueries({ queryKey: queryKeys.holdings })
      queryClient.invalidateQueries({ queryKey: queryKeys.correlation })
      queryClient.invalidateQueries({ queryKey: queryKeys.risk })
      queryClient.invalidateQueries({ queryKey: queryKeys.opportunities() })
      queryClient.invalidateQueries({ queryKey: queryKeys.hotThemes() })
      queryClient.invalidateQueries({ queryKey: queryKeys.backtestSensitivity })
      queryClient.invalidateQueries({ queryKey: queryKeys.backtestSnapshotStats })
      queryClient.invalidateQueries({ queryKey: queryKeys.syncLogs })
    },
  })
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateStrategy,
    onSuccess: (data: StrategyConfig) => {
      queryClient.setQueryData(queryKeys.strategy, data)
      queryClient.invalidateQueries({ queryKey: queryKeys.signals })
    },
  })
}
