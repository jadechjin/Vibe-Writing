"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"

export type JobHandle = {
  workflow_id: string | null
  job_id: string
  status: string
}

export type ManifestDetail = {
  id: string
  projectId: string
  systemId: string
  version: number
  status: string
  manifestJson: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export type ManifestCreateAcceptedResponse = {
  handle: JobHandle
}

export type ManifestConfirmResponse = {
  id: string
  systemId: string
  status: string
  confirmedAt: string
}

export type AssetQCConfirmResponse = {
  id: string
  assetId: string
  qcStatus: string
  confirmedAt: string
}

const manifestKeys = {
  detail: (systemId: string) => ["manifest", systemId] as const,
  preview: (systemId: string) => ["manifest-preview", systemId] as const,
}

export function useManifest(systemId: string) {
  return useQuery({
    queryKey: manifestKeys.detail(systemId),
    queryFn: () => apiRequest<ManifestDetail | null>(`/systems/${systemId}/manifest`),
    enabled: !!systemId,
    refetchInterval: 10_000,
  })
}

export function useGenerateManifest(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiRequest<ManifestCreateAcceptedResponse>(`/systems/${systemId}/manifest`, {
        method: "POST",
        body: JSON.stringify({ status: "draft" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: manifestKeys.detail(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useConfirmManifest(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (manifestId: string) =>
      apiRequest<ManifestConfirmResponse>(`/manifests/${manifestId}/confirm`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: manifestKeys.detail(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useConfirmAssetQC(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (assetId: string) =>
      apiRequest<AssetQCConfirmResponse>(`/assets/${assetId}/confirm-qc`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets", systemId] })
      queryClient.invalidateQueries({ queryKey: manifestKeys.detail(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export type BatchConfirmAssetQCResponse = {
  succeeded: string[]
  failed: Array<{ assetId: string; reason: string }>
}

export function useBatchConfirmAssetQC(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (assetIds: string[]) =>
      apiRequest<BatchConfirmAssetQCResponse>(`/systems/${systemId}/assets/batch-confirm-qc`, {
        method: "POST",
        body: JSON.stringify({ asset_ids: assetIds }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets", systemId] })
      queryClient.invalidateQueries({ queryKey: manifestKeys.detail(systemId) })
      queryClient.invalidateQueries({ queryKey: manifestKeys.preview(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export type ManifestPlanAsset = {
  id: string
  fileName: string
  assetType: string
  mimeType: string | null
  qcStatus: string | null
}

export type ManifestPlanAnalysis = {
  id: string
  status: string
  summary: string | null
}

export type ManifestFigurePlanEntry = {
  figurePlanId: string
  figureNo: string
  title: string
  sectionKey: string | null
  dataQuestion: string | null
  evidenceText: string | null
  assets: ManifestPlanAsset[]
  latestAnalysis: ManifestPlanAnalysis | null
  completeness: "complete" | "missing_assets" | "missing_evidence"
}

export type ManifestIssue = {
  severity: "blocker" | "warning"
  rule: string
  scope: string
  message: string
  detail: string | null
  resolution: string | null
}

export type ManifestSummaryStats = {
  totalPlans: number
  completePlans: number
  incompletePlans: number
  totalAssets: number
  confirmedAssets: number
  orphanAssets: number
  blockerCount: number
  warningCount: number
}

export type ManifestPreview = {
  systemId: string
  summary: ManifestSummaryStats
  figurePlans: ManifestFigurePlanEntry[]
  orphanAssets: ManifestPlanAsset[]
  issues: ManifestIssue[]
  manifest: ManifestDetail | null
}

export function useConfirmManifestFromPreview(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiRequest<ManifestConfirmResponse>(`/systems/${systemId}/manifest-confirm`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: manifestKeys.detail(systemId) })
      queryClient.invalidateQueries({ queryKey: manifestKeys.preview(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useManifestPreview(systemId: string) {
  return useQuery({
    queryKey: manifestKeys.preview(systemId),
    queryFn: () => apiRequest<ManifestPreview>(`/systems/${systemId}/manifest-preview`),
    enabled: !!systemId,
    refetchInterval: 15_000,
  })
}
