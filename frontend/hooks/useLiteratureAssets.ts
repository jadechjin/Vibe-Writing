"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import type { AssetDetail } from "./useAnalysis"
import { useUploadAsset } from "./useAnalysis"

const literatureKeys = {
  list: (systemId: string) => ["literature-assets", systemId] as const,
}

export function useLiteratureAssets(systemId: string) {
  return useQuery({
    queryKey: literatureKeys.list(systemId),
    queryFn: async () => {
      const all = await apiRequest<AssetDetail[]>(`/systems/${systemId}/assets`)
      return all.filter((a) => a.assetType === "reference_literature")
    },
    enabled: !!systemId,
  })
}

export function useDeleteLiteratureAsset(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (assetId: string) =>
      apiRequest<void>(`/assets/${assetId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: literatureKeys.list(systemId) })
    },
  })
}

export { useUploadAsset }
