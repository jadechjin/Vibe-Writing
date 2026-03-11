"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import { applySystemStateToSnapshot, type WorkflowSnapshot } from "./useProjectStatus"

export type JobHandle = {
  workflow_id: string | null
  job_id: string
  status: string
}

export type AssetMetadataDetail = {
  id: string
  assetId: string
  semanticDescription: string | null
  sourceDescription: string | null
  instrumentInfo: string | null
  sampleIds: string[] | null
  conditionsJson: Record<string, unknown> | null
  qcStatus: string
  createdAt: string
  updatedAt: string
}

export type AssetDetail = {
  id: string
  projectId: string
  systemId: string
  assetType: string
  fileName: string
  storageKey: string
  mimeType: string | null
  version: number
  uploadedBy: string
  createdAt: string
  updatedAt: string
  metadataEntry: AssetMetadataDetail | null
}

export type AnalysisRunDetail = {
  id: string
  systemId: string
  assetId: string | null
  runType: string
  status: string
  inputPayloadJson: Record<string, unknown>
  resultPayloadJson: Record<string, unknown>
  summary: string | null
  version: number
  startedAt: string
  completedAt: string | null
  createdAt: string
  updatedAt: string
}

export type AnalysisRunCreateAcceptedResponse = {
  handle: JobHandle
}

export type AssetUploadInput = {
  assetType: string
  fileName: string
  storageKey: string
  mimeType?: string
  uploadedBy: string
}

export type AssetBindInput = {
  semanticDescription?: string
  sourceDescription?: string
  instrumentInfo?: string
  sampleIds?: string[]
  conditionsJson?: Record<string, unknown>
  analysisRunId?: string
}

const analysisKeys = {
  assets: (systemId: string) => ["assets", systemId] as const,
  runs: (systemId: string) => ["analysis-runs", systemId] as const,
}

const UPLOAD_RESET_STATES = new Set([
  "Figure_Plan_Ready",
  "Data_Pending",
  "Data_Uploaded",
  "Analysis_Ready",
])

const DOWNSTREAM_ASSET_CONFIRMATION_STATES = new Set([
  "Assets_Confirmed",
  "Evidence_Matrix_Ready",
  "Outline_Ready",
  "Section_Drafting",
  "Chapter_Review",
  "Chapter_Approved",
])

function updateWorkflowSnapshotState(
  queryClient: ReturnType<typeof useQueryClient>,
  systemId: string,
  systemState: string,
) {
  queryClient.setQueryData<WorkflowSnapshot | null>(["workflow", systemId], (current) =>
    applySystemStateToSnapshot(current ?? null, systemState),
  )
}

export function useAssets(systemId: string) {
  return useQuery({
    queryKey: analysisKeys.assets(systemId),
    queryFn: () => apiRequest<AssetDetail[]>(`/systems/${systemId}/assets`),
    enabled: !!systemId,
    refetchInterval: 10_000,
  })
}

export function useUploadAsset(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: AssetUploadInput) =>
      apiRequest<AssetDetail>(`/assets/upload`, {
        method: "POST",
        body: JSON.stringify({ systemId, ...input }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: analysisKeys.assets(systemId) })
      queryClient.invalidateQueries({ queryKey: ["manifest", systemId] })

      const currentState = queryClient.getQueryData<WorkflowSnapshot | null>(["workflow", systemId])?.currentState
      if (currentState && UPLOAD_RESET_STATES.has(currentState)) {
        updateWorkflowSnapshotState(queryClient, systemId, "Data_Uploaded")
      } else if (currentState && DOWNSTREAM_ASSET_CONFIRMATION_STATES.has(currentState)) {
        updateWorkflowSnapshotState(queryClient, systemId, "Analysis_Ready")
      }

      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useBindAssetMetadata(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ assetId, input }: { assetId: string; input: AssetBindInput }) =>
      apiRequest<AssetDetail>(`/assets/${assetId}/bind`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: analysisKeys.assets(systemId) })
      queryClient.invalidateQueries({ queryKey: ["manifest", systemId] })

      const currentState = queryClient.getQueryData<WorkflowSnapshot | null>(["workflow", systemId])?.currentState
      if (currentState && DOWNSTREAM_ASSET_CONFIRMATION_STATES.has(currentState)) {
        updateWorkflowSnapshotState(queryClient, systemId, "Analysis_Ready")
      }

      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useAnalysisRuns(systemId: string) {
  return useQuery({
    queryKey: analysisKeys.runs(systemId),
    queryFn: () => apiRequest<AnalysisRunDetail[]>(`/systems/${systemId}/analysis-runs`),
    enabled: !!systemId,
    refetchInterval: 10_000,
  })
}

export function useCreateAnalysisRun(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiRequest<AnalysisRunCreateAcceptedResponse>(`/systems/${systemId}/analysis-runs`, {
        method: "POST",
        body: JSON.stringify({ runType: "default" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: analysisKeys.runs(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}
