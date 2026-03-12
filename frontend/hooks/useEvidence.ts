"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import { applySystemStateToSnapshot, type WorkflowSnapshot } from "./useProjectStatus"

export type JobHandle = {
  workflow_id: string | null
  job_id: string
  status: string
}

export type ClaimDetail = {
  id: string
  systemId: string
  claimId: string
  statement: string
  sectionRef: string | null
  confidenceLevel: string
  status: string
  version: number
  approvedAt: string | null
  createdAt: string
  updatedAt: string
}

export type ClaimEvidenceLinkDetail = {
  id: string
  claimRecordId: string
  assetId: string
  analysisRunId: string | null
  statisticalSupport: Record<string, unknown>
  createdAt: string
}

export type OutlineAssetBindingDetail = {
  id: string
  outlineId: string
  assetId: string
  sectionKey: string
  bindingNote: string | null
  createdAt: string
  updatedAt: string
}

export type OutlineDetail = {
  id: string
  systemId: string
  version: number
  outlineJson: Record<string, unknown> | Array<Record<string, unknown>>
  status: string
  generatedFromClaimsJson: string[]
  bindings: OutlineAssetBindingDetail[]
  approvedAt: string | null
  createdAt: string
  updatedAt: string
}

export type OutlineGenerateAcceptedResponse = {
  handle: JobHandle
}

export type EvidenceMatrixGenerateAcceptedResponse = {
  handle: JobHandle
}

export type OutlineBindingInput = {
  assetId: string
  sectionKey: string
  description?: string
}

export type ClaimEvidenceLinkInput = {
  assetId: string
  analysisRunId?: string
  statisticalSupport?: Record<string, unknown>
}

const evidenceKeys = {
  claims: (systemId: string) => ["claims", systemId] as const,
  outlines: (systemId: string) => ["outlines", systemId] as const,
}

function updateWorkflowSnapshotState(
  queryClient: ReturnType<typeof useQueryClient>,
  systemId: string,
  systemState: string,
) {
  queryClient.setQueryData<WorkflowSnapshot | null>(["workflow", systemId], (current) =>
    applySystemStateToSnapshot(current ?? null, systemState),
  )
}

export function useClaims(systemId: string) {
  return useQuery({
    queryKey: evidenceKeys.claims(systemId),
    queryFn: () => apiRequest<ClaimDetail[]>(`/systems/${systemId}/claims`),
    enabled: !!systemId,
  })
}

export function useOutlines(systemId: string) {
  return useQuery({
    queryKey: evidenceKeys.outlines(systemId),
    queryFn: () => apiRequest<OutlineDetail[]>(`/systems/${systemId}/outlines`),
    enabled: !!systemId,
  })
}

export function useGenerateEvidenceMatrix(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiRequest<EvidenceMatrixGenerateAcceptedResponse>(
        `/systems/${systemId}/evidence-matrix/generate`,
        {
          method: "POST",
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKeys.claims(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useApproveClaim(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (claimId: string) =>
      apiRequest<ClaimDetail>(`/claims/${claimId}`, {
        method: "PATCH",
        body: JSON.stringify({ status: "approved" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKeys.claims(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useCreateClaimEvidenceLink(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ claimId, input }: { claimId: string; input: ClaimEvidenceLinkInput }) =>
      apiRequest<ClaimEvidenceLinkDetail>(`/claims/${claimId}/evidence-links`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKeys.claims(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useGenerateOutline(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiRequest<OutlineGenerateAcceptedResponse>(`/systems/${systemId}/outline/generate`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKeys.outlines(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useConfirmOutline(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (outlineId: string) =>
      apiRequest<OutlineDetail>(`/outlines/${outlineId}/confirm`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKeys.outlines(systemId) })
      updateWorkflowSnapshotState(queryClient, systemId, "Outline_Ready")
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useCreateOutlineBinding(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ outlineId, input }: { outlineId: string; input: OutlineBindingInput }) =>
      apiRequest<OutlineAssetBindingDetail>(`/outlines/${outlineId}/bindings`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKeys.outlines(systemId) })
    },
  })
}

export type BatchApproveClaimsResponse = {
  succeeded: string[]
  failed: Array<{ claimId: string; reason: string }>
}

export function useBatchApproveClaims(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (claimIds: string[]) =>
      apiRequest<BatchApproveClaimsResponse>(`/systems/${systemId}/claims/batch-approve`, {
        method: "POST",
        body: JSON.stringify({ claim_ids: claimIds }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: evidenceKeys.claims(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}
