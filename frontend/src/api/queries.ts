import {
  api,
  fetchBacktestSensitivity,
  fetchBacktestSnapshotStats,
  fetchCorrelation,
  fetchHotThemes,
  fetchOpportunities,
  fetchRisk,
  fetchSignals,
  fetchStrategy,
  fetchThemeCandidates,
  fetchThemes,
  searchFunds,
  syncData,
  updateStrategy,
} from './client'

// ── Query Keys ──

export const queryKeys = {
  overview: ['overview'] as const,
  holdings: ['holdings'] as const,
  signals: ['signals'] as const,
  correlation: ['correlation'] as const,
  risk: ['risk'] as const,
  strategy: ['strategy'] as const,
  opportunities: (params?: Record<string, unknown>) =>
    ['opportunities', params] as const,
  hotThemes: (params?: Record<string, unknown>) =>
    ['hotThemes', params] as const,
  backtestSensitivity: ['backtestSensitivity'] as const,
  backtestSnapshotStats: ['backtestSnapshotStats'] as const,
  syncLogs: ['syncLogs'] as const,
  themes: ['themes'] as const,
  themeCandidates: (themeId: string, sortBy: string, limit: number) =>
    ['themeCandidates', themeId, sortBy, limit] as const,
}

// ── Query Functions ──

export async function fetchOverview() {
  return api.get<import('../types').Overview>('/api/portfolio/overview')
}

export async function fetchHoldings() {
  return api.get<import('../types').Overview>('/api/portfolio/holdings')
}

export { fetchBacktestSensitivity, fetchBacktestSnapshotStats }
export { fetchCorrelation }
export { fetchRisk }
export { fetchSignals }
export { fetchStrategy }
export { fetchOpportunities }
export { fetchHotThemes }
export { syncData }
export { updateStrategy }
export { searchFunds }
export { fetchThemes }
export { fetchThemeCandidates }

export async function fetchSyncLogs(limit = 3) {
  return api.get<{ logs: import('../types').SyncLogEntry[] }>(
    `/api/settings/sync-logs?limit=${limit}`,
  )
}
