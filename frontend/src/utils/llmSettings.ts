const STORAGE_API_KEY = 'fund-quant.llm.apiKey'
const STORAGE_BASE_URL = 'fund-quant.llm.baseUrl'
const STORAGE_MODEL = 'fund-quant.llm.model'

export const DEFAULT_LLM_BASE_URL = 'https://api.deepseek.com'
export const DEFAULT_LLM_MODEL = 'deepseek-v4-flash'

export interface LlmRequestOverrides {
  api_key?: string
  base_url?: string
  model?: string
}

export function getLlmApiKey(): string {
  return localStorage.getItem(STORAGE_API_KEY) ?? ''
}

export function getLlmBaseUrl(): string {
  return localStorage.getItem(STORAGE_BASE_URL) ?? DEFAULT_LLM_BASE_URL
}

export function getLlmModel(): string {
  return localStorage.getItem(STORAGE_MODEL) ?? DEFAULT_LLM_MODEL
}

export function saveLlmSettings(apiKey: string, baseUrl: string, model: string) {
  const trimmedKey = apiKey.trim()
  if (trimmedKey) {
    localStorage.setItem(STORAGE_API_KEY, trimmedKey)
  } else {
    localStorage.removeItem(STORAGE_API_KEY)
  }

  const trimmedUrl = baseUrl.trim() || DEFAULT_LLM_BASE_URL
  if (trimmedUrl === DEFAULT_LLM_BASE_URL) {
    localStorage.removeItem(STORAGE_BASE_URL)
  } else {
    localStorage.setItem(STORAGE_BASE_URL, trimmedUrl)
  }

  const trimmedModel = model.trim() || DEFAULT_LLM_MODEL
  if (trimmedModel === DEFAULT_LLM_MODEL) {
    localStorage.removeItem(STORAGE_MODEL)
  } else {
    localStorage.setItem(STORAGE_MODEL, trimmedModel)
  }
}

export function getLlmRequestOverrides(): LlmRequestOverrides {
  const apiKey = getLlmApiKey()
  if (!apiKey) return {}
  return {
    api_key: apiKey,
    base_url: getLlmBaseUrl(),
    model: getLlmModel(),
  }
}
