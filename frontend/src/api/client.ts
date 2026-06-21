import type {
  CorrelationOut,
  OcrConfirmResponse,
  OcrUploadResponse,
  RiskOut,
  SignalsListOut,
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
