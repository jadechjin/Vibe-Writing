"use client"

import { useQuery } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"

export type AnalysisRunSummary = {
  id: string
  status: string
  summary: string | null
  confidence: number | null
  updatedAt: string | null
}

export type ImageAssetDetail = {
  id: string
  fileName: string
  mimeType: string | null
  previewUrl: string | null
}

export type ImageAnalysisItem = {
  figurePlanId: string
  figureNo: string
  title: string
  sectionKey: string | null
  dataQuestion: string | null
  evidenceText: string | null
  assets: ImageAssetDetail[]
  latestAnalysis: AnalysisRunSummary | null
}

export type ImageAnalysisListResponse = {
  items: ImageAnalysisItem[]
  total: number
  analyzed: number
  pending: number
}

const imageAnalysisKeys = {
  list: (systemId: string) => ["image-analyses", systemId] as const,
}

export function useImageAnalyses(systemId: string) {
  return useQuery({
    queryKey: imageAnalysisKeys.list(systemId),
    queryFn: () => apiRequest<ImageAnalysisListResponse>(`/systems/${systemId}/image-analyses`),
    enabled: !!systemId,
    refetchInterval: 15_000,
  })
}
