"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api"
const STREAMING_API_BASE_URL = process.env.NEXT_PUBLIC_STREAMING_API_URL ?? API_BASE_URL

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type FigurePlanAssetDetail = {
  id: string
  figurePlanId: string
  assetId: string
  role: string
  position: number
  fileName: string
  mimeType: string | null
  previewUrl: string | null
  createdAt: string
}

export type ChatMessageDetail = {
  id: string
  sessionId: string
  role: string
  content: string
  status: string
  turnIndex: number
  errorText: string | null
  createdAt: string
}

// ---------------------------------------------------------------------------
// Query keys
// ---------------------------------------------------------------------------

const figurePlanAssetKeys = {
  list: (planId: string) => ["figure-plan-assets", planId] as const,
}

const chatKeys = {
  messages: (planId: string, provider: string, scope: string) => ["figure-plan-chat", planId, provider, scope] as const,
}

// ---------------------------------------------------------------------------
// FigurePlanAsset hooks
// ---------------------------------------------------------------------------

export function useFigurePlanAssets(planId: string) {
  return useQuery({
    queryKey: figurePlanAssetKeys.list(planId),
    queryFn: () => apiRequest<FigurePlanAssetDetail[]>(`/figure-plans/${planId}/assets`),
    enabled: !!planId,
  })
}

export function useUploadFigurePlanAsset(planId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (file: File) => {
      const formData = new FormData()
      formData.append("file", file)
      formData.append("role", "source_image")
      return apiRequest<FigurePlanAssetDetail>(`/figure-plans/${planId}/assets`, {
        method: "POST",
        body: formData,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanAssetKeys.list(planId) })
    },
  })
}

export function useDeleteFigurePlanAsset(planId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (bindingId: string) =>
      apiRequest<void>(`/figure-plans/${planId}/assets/${bindingId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanAssetKeys.list(planId) })
    },
  })
}

// ---------------------------------------------------------------------------
// FigurePlanChat hooks
// ---------------------------------------------------------------------------

export function useChatMessages(planId: string, provider: string, scope: string = "planning") {
  return useQuery({
    queryKey: chatKeys.messages(planId, provider, scope),
    queryFn: () =>
      apiRequest<ChatMessageDetail[]>(`/figure-plans/${planId}/chat/messages`, {
        query: { provider, scope },
      }),
    enabled: !!planId && !!provider,
  })
}

export type ChatStreamCallbacks = {
  onDelta: (text: string) => void
  onDone: () => void
  onError: (error: string) => void
}

export async function sendChatMessageStream(
  planId: string,
  provider: string,
  content: string,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal,
  scope: string = "planning",
): Promise<void> {
  const url = `${STREAMING_API_BASE_URL}/figure-plans/${planId}/chat/messages`
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ provider, content, scope }),
    signal,
  })

  if (!response.ok || !response.body) {
    callbacks.onError(`请求失败: ${response.status}`)
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue
        const payload = line.slice(6).trim()
        if (!payload) continue

        try {
          const event = JSON.parse(payload) as { type: string; content: string }
          if (event.type === "delta") {
            callbacks.onDelta(event.content)
          } else if (event.type === "done") {
            callbacks.onDone()
          } else if (event.type === "error") {
            callbacks.onError(event.content)
          }
        } catch {
          // non-JSON SSE line, ignore
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}
