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

export class ApiError extends Error {
  readonly status: number
  readonly serverError: string | undefined

  constructor(status: number, serverError?: string) {
    super(serverError ?? `Request failed with status ${status}`)
    this.name = "ApiError"
    this.status = status
    this.serverError = serverError
  }
}

type RequestOptions = RequestInit & {
  query?: Record<string, string | number | boolean | undefined>
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
    try {
      const body = (await response.json()) as ApiResponse<unknown>
      serverError = body.error ?? undefined
    } catch {
      // non-JSON error body
    }
    throw new ApiError(response.status, serverError)
  }

  const body = (await response.json()) as ApiResponse<T>

  if (!body.success && body.error) {
    throw new ApiError(response.status, body.error)
  }

  return body.data as T
}
