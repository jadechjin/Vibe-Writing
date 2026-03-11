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
