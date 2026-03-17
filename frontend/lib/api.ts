const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api"

export type ApiResponse<T> = {
  success: boolean
  data?: T
  error?: string
  meta?: {
    total?: number
    page?: number
    limit?: number
  }
}

export type ApiErrorPayload = {
  code?: string
  details?: Record<string, unknown>
}

export class ApiError extends Error {
  readonly status: number
  readonly serverError: string | undefined
  readonly code: string | undefined
  readonly details: Record<string, unknown>

  constructor(status: number, serverError?: string, payload: ApiErrorPayload = {}) {
    super(serverError ?? `Request failed with status ${status}`)
    this.name = "ApiError"
    this.status = status
    this.serverError = serverError
    this.code = payload.code
    this.details = payload.details ?? {}
  }
}

type RequestOptions = RequestInit & {
  query?: Record<string, string | number | boolean | undefined>
}

function extractApiErrorPayload(data: unknown): ApiErrorPayload {
  if (!data || typeof data !== "object" || Array.isArray(data)) {
    return {}
  }

  const payload = data as Record<string, unknown>
  return {
    code: typeof payload.code === "string" ? payload.code : undefined,
    details:
      payload.details && typeof payload.details === "object" && !Array.isArray(payload.details)
        ? (payload.details as Record<string, unknown>)
        : undefined,
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`)

  if (options.query) {
    Object.entries(options.query).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.set(key, String(value))
      }
    })
  }

  const headers = new Headers(options.headers)
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData

  if (!isFormData && options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (!response.ok) {
    let serverError: string | undefined
    let payload: ApiErrorPayload = {}
    try {
      const body = (await response.json()) as ApiResponse<unknown>
      serverError = body.error ?? undefined
      payload = extractApiErrorPayload(body.data)
    } catch {
      // non-JSON error body
    }
    throw new ApiError(response.status, serverError, payload)
  }

  if (response.status === 204) {
    return undefined as T
  }

  const body = (await response.json()) as ApiResponse<T>

  if (!body.success && body.error) {
    throw new ApiError(response.status, body.error, extractApiErrorPayload(body.data))
  }

  return body.data as T
}
