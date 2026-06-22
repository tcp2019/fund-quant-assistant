import type {
  CorrelationOut,
  DataSyncResult,
  FundSearchOut,
  OcrConfirmResponse,
  OcrUploadResponse,
  OpportunitiesOut,
  RiskOut,
  SignalsListOut,
  StrategyConfig,
  ThemeCandidatesOut,
  ThemeOption,
} from '../types'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `Request failed: ${response.status}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

async function parseErrorMessage(response: Response): Promise<string> {
  const message = await response.text()
  if (!message) {
    return `Request failed: ${response.status}`
  }

  try {
    const parsed = JSON.parse(message) as { detail?: string | { msg?: string }[] }
    if (typeof parsed.detail === 'string') {
      return parsed.detail
    }
    if (Array.isArray(parsed.detail)) {
      return parsed.detail.map((item) => item.msg ?? String(item)).join('; ')
    }
  } catch {
    // fall through to raw message
  }

  return message
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
}

export async function uploadOcr(params: {
  platform: string
  text?: string
  file?: File | null
}): Promise<OcrUploadResponse> {
  if (params.file) {
    const formData = new FormData()
    formData.append('platform', params.platform)
    formData.append('file', params.file)

    const response = await fetch('/api/ocr/upload', {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      throw new Error(await parseErrorMessage(response))
    }

    return response.json() as Promise<OcrUploadResponse>
  }

  return api.post<OcrUploadResponse>('/api/ocr/upload', {
    platform: params.platform,
    text: params.text ?? '',
  })
}

export async function confirmOcr(
  jobId: number,
  holdings: OcrUploadResponse['holdings'],
): Promise<OcrConfirmResponse> {
  return api.post<OcrConfirmResponse>(`/api/ocr/${jobId}/confirm`, { holdings })
}

export async function fetchSignals(): Promise<SignalsListOut> {
  return api.get<SignalsListOut>('/api/signals')
}

export async function fetchCorrelation(): Promise<CorrelationOut> {
  return api.get<CorrelationOut>('/api/analysis/correlation')
}

export async function fetchRisk(): Promise<RiskOut> {
  return api.get<RiskOut>('/api/analysis/risk')
}

export async function fetchStrategy(): Promise<StrategyConfig> {
  return api.get<StrategyConfig>('/api/settings/strategy')
}

export async function updateStrategy(body: {
  template_name: string
  target_weights?: Record<string, number>
  thresholds?: StrategyConfig['thresholds']
  intra_category_mode?: StrategyConfig['intra_category_mode']
  fund_target_weights?: Record<string, number>
}): Promise<StrategyConfig> {
  return api.put<StrategyConfig>('/api/settings/strategy', body)
}

export async function syncData(): Promise<DataSyncResult> {
  return api.post<DataSyncResult>('/api/data/sync', {})
}

export async function searchFunds(query: string, limit = 8): Promise<FundSearchOut> {
  const params = new URLSearchParams({ q: query, limit: String(limit) })
  return api.get<FundSearchOut>(`/api/funds/search?${params.toString()}`)
}

export async function refreshFundCatalog(): Promise<{ count: number }> {
  return api.post<{ count: number }>('/api/funds/catalog/refresh', {})
}

export async function fetchThemes(): Promise<ThemeOption[]> {
  return api.get<ThemeOption[]>('/api/funds/themes')
}

export async function fetchThemeCandidates(
  themeId: string,
  sortBy = 'return_1m',
  limit = 5,
): Promise<ThemeCandidatesOut> {
  const params = new URLSearchParams({ sort_by: sortBy, limit: String(limit) })
  return api.get<ThemeCandidatesOut>(`/api/funds/themes/${themeId}/candidates?${params.toString()}`)
}

export async function fetchOpportunities(params?: {
  sell_limit?: number
  buy_limit?: number
  explore_limit?: number
  theme_limit?: number
}): Promise<OpportunitiesOut> {
  const search = new URLSearchParams()
  if (params?.sell_limit) search.set('sell_limit', String(params.sell_limit))
  if (params?.buy_limit) search.set('buy_limit', String(params.buy_limit))
  if (params?.explore_limit) search.set('explore_limit', String(params.explore_limit))
  if (params?.theme_limit) search.set('theme_limit', String(params.theme_limit))
  const qs = search.toString()
  return api.get<OpportunitiesOut>(`/api/opportunities${qs ? `?${qs}` : ''}`)
}
