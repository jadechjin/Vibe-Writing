"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import { applySystemStateToSnapshot, type WorkflowSnapshot } from "./useProjectStatus"

export type JobHandle = {
  workflow_id: string | null
  job_id: string
  status: string
}

export type ReviewCommentDetail = {
  id: string
  draftId: string
  commenterId: string
  commentText: string
  decision: string | null
  contextJson: Record<string, unknown>
  resolvedAt: string | null
  createdAt: string
  updatedAt: string
}

export type SectionDraftDetail = {
  id: string
  systemId: string
  outlineId: string | null
  sectionKey: string
  version: number
  contentMd: string
  status: string
  generatedFromClaimsJson: string[]
  traceabilityJson: Array<Record<string, unknown>>
  traceabilityStale: boolean
  reviewComments: ReviewCommentDetail[]
  approvedAt: string | null
  createdAt: string
  updatedAt: string
}

export type DraftGenerateAcceptedResponse = {
  handle: JobHandle
}

export type ReviewInput = {
  commenterId: string
  commentText: string
  decision?: "approve" | "request_changes" | "freeze"
}

const draftKeys = {
  list: (systemId: string) => ["drafts", systemId] as const,
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

export function useDrafts(systemId: string) {
  return useQuery({
    queryKey: draftKeys.list(systemId),
    queryFn: () => apiRequest<SectionDraftDetail[]>(`/systems/${systemId}/drafts`),
    enabled: !!systemId,
  })
}

export function useGenerateSectionDraft(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ sectionKey, claimIds, outlineId }: { sectionKey: string; claimIds: string[]; outlineId: string }) =>
      apiRequest<DraftGenerateAcceptedResponse>(
        `/systems/${systemId}/sections/${sectionKey}/draft`,
        {
          method: "POST",
          body: JSON.stringify({ claimIds, outlineId }),
        },
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: draftKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useApproveDraft(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (draftId: string) =>
      apiRequest<SectionDraftDetail>(`/drafts/${draftId}/approve`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: draftKeys.list(systemId) })
      updateWorkflowSnapshotState(queryClient, systemId, "Chapter_Review")
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useAddReviewComment(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ draftId, input }: { draftId: string; input: ReviewInput }) =>
      apiRequest<ReviewCommentDetail>(`/drafts/${draftId}/review`, {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: draftKeys.list(systemId) })
    },
  })
}
