"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"

export type JobHandle = {
  workflow_id: string | null
  job_id: string
  status: string
}

export type SkeletonSummary = {
  id: string
  version: number
  status: string
  changeSummary: string | null
  createdAt: string
}

export type SkeletonDetail = {
  id: string
  systemId: string
  version: number
  skeletonJson: Record<string, unknown>
  changeSummary: string | null
  sourceAssetIds: string[]
  status: string
  confirmedAt: string | null
  createdAt: string
  updatedAt: string
}

export type SkeletonConfirmResponse = {
  skeleton: SkeletonDetail
  affectedClaims: Array<{ claimId: string; sectionRef: string }>
}

export type SkeletonGenerateInput = {
  sourceAssetIds?: string[]
  userIntent?: string
  provider?: "claude" | "codex" | "gemini"
  customPrompt?: string | null
}

export type BuildPromptInput = {
  sourceAssetIds?: string[]
  userIntent?: string
  provider?: "claude" | "codex" | "gemini"
}

export type BuildPromptResult = {
  prompt: string
  provider: string
  fileDir: string
  fileList: string[]
}

export type SkeletonReviseInput = {
  skeletonId: string
  feedback: string
}

export type SkeletonPatchInput = {
  skeletonJson?: Record<string, unknown>
  changeSummary?: string
}

const skeletonKeys = {
  list: (systemId: string) => ["skeletons", systemId] as const,
  detail: (skeletonId: string) => ["skeleton", skeletonId] as const,
}

function normalizeSkeletonSummary(raw: Record<string, unknown>): SkeletonSummary {
  return {
    id: raw.id as string,
    version: raw.version as number,
    status: raw.status as string,
    changeSummary: (raw.change_summary ?? raw.changeSummary ?? null) as string | null,
    createdAt: (raw.created_at ?? raw.createdAt ?? "") as string,
  }
}

function normalizeSkeletonDetail(raw: Record<string, unknown>): SkeletonDetail {
  return {
    id: raw.id as string,
    systemId: (raw.system_id ?? raw.systemId ?? "") as string,
    version: raw.version as number,
    skeletonJson: (raw.skeleton_json ?? raw.skeletonJson ?? {}) as Record<string, unknown>,
    changeSummary: (raw.change_summary ?? raw.changeSummary ?? null) as string | null,
    sourceAssetIds: (raw.source_asset_ids ?? raw.sourceAssetIds ?? []) as string[],
    status: raw.status as string,
    confirmedAt: (raw.confirmed_at ?? raw.confirmedAt ?? null) as string | null,
    createdAt: (raw.created_at ?? raw.createdAt ?? "") as string,
    updatedAt: (raw.updated_at ?? raw.updatedAt ?? "") as string,
  }
}

export function useSkeletons(systemId: string) {
  return useQuery({
    queryKey: skeletonKeys.list(systemId),
    queryFn: async () => {
      const raw = await apiRequest<Record<string, unknown>[]>(`/systems/${systemId}/skeletons`)
      return raw.map(normalizeSkeletonSummary)
    },
    enabled: !!systemId,
  })
}

export function useSkeleton(skeletonId: string) {
  return useQuery({
    queryKey: skeletonKeys.detail(skeletonId),
    queryFn: async () => {
      const raw = await apiRequest<Record<string, unknown>>(`/skeletons/${skeletonId}`)
      return normalizeSkeletonDetail(raw)
    },
    enabled: !!skeletonId,
  })
}

export function useGenerateSkeleton(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: SkeletonGenerateInput = {}) =>
      apiRequest<{ handle: JobHandle }>(`/systems/${systemId}/skeletons/generate`, {
        method: "POST",
        body: JSON.stringify({
          source_asset_ids: input.sourceAssetIds ?? [],
          user_intent: input.userIntent ?? "",
          provider: input.provider ?? "claude",
          custom_prompt: input.customPrompt ?? null,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skeletonKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

function normalizeBuildPromptResult(raw: Record<string, unknown>): BuildPromptResult {
  return {
    prompt: (raw.prompt ?? "") as string,
    provider: (raw.provider ?? "") as string,
    fileDir: (raw.file_dir ?? raw.fileDir ?? "") as string,
    fileList: (raw.file_list ?? raw.fileList ?? []) as string[],
  }
}

export function useBuildPrompt(systemId: string) {
  return useMutation({
    mutationFn: (input: BuildPromptInput = {}) =>
      apiRequest<Record<string, unknown>>(`/systems/${systemId}/skeletons/build-prompt`, {
        method: "POST",
        body: JSON.stringify({
          source_asset_ids: input.sourceAssetIds ?? [],
          user_intent: input.userIntent ?? "",
          provider: input.provider ?? "claude",
        }),
      }).then(normalizeBuildPromptResult),
  })
}

export function useReviseSkeleton(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: SkeletonReviseInput) =>
      apiRequest<{ handle: JobHandle }>(`/systems/${systemId}/skeletons/revise`, {
        method: "POST",
        body: JSON.stringify({
          skeleton_id: input.skeletonId,
          feedback: input.feedback,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skeletonKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function usePatchSkeleton(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ skeletonId, input }: { skeletonId: string; input: SkeletonPatchInput }) =>
      apiRequest<Record<string, unknown>>(`/skeletons/${skeletonId}`, {
        method: "PATCH",
        body: JSON.stringify({
          skeleton_json: input.skeletonJson,
          change_summary: input.changeSummary,
        }),
      }),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(
        skeletonKeys.detail(variables.skeletonId),
        normalizeSkeletonDetail(data),
      )
      queryClient.invalidateQueries({ queryKey: skeletonKeys.list(systemId) })
    },
  })
}

export function useConfirmSkeleton(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (skeletonId: string) =>
      apiRequest<Record<string, unknown>>(`/skeletons/${skeletonId}/confirm`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skeletonKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useDeleteSkeleton(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (skeletonId: string) =>
      apiRequest<void>(`/skeletons/${skeletonId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: skeletonKeys.list(systemId) })
    },
  })
}
