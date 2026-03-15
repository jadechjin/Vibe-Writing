"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"

export type JobHandle = {
  workflow_id: string | null
  job_id: string
  status: string
}

export type FigurePlanDetail = {
  id: string
  systemId: string
  figureNo: string
  title: string
  claimText: string
  dataNeededJson: Array<Record<string, unknown>> | Record<string, unknown>
  methodJson: Record<string, unknown>
  acceptanceCriteriaJson: Array<Record<string, unknown>> | Record<string, unknown>
  status: string
  version: number
  sectionKey: string | null
  skeletonVersion: number | null
  briefText: string | null
  briefConfirmedAt: string | null
  createdAt: string
  updatedAt: string
}

export type FigurePlanGenerateAcceptedResponse = {
  handle: JobHandle
}

export type FigurePlanPatchInput = {
  figureNo?: string
  title?: string
  claimText?: string
  sectionKey?: string | null
  dataNeededJson?: Array<Record<string, unknown>> | Record<string, unknown>
  methodJson?: Record<string, unknown>
  acceptanceCriteriaJson?: Array<Record<string, unknown>> | Record<string, unknown>
  briefText?: string | null
}

const figurePlanKeys = {
  list: (systemId: string) => ["figure-plans", systemId] as const,
}

export function useFigurePlans(systemId: string) {
  return useQuery({
    queryKey: figurePlanKeys.list(systemId),
    queryFn: () => apiRequest<FigurePlanDetail[]>(`/systems/${systemId}/figure-plans`),
    enabled: !!systemId,
    refetchInterval: 10_000,
  })
}

export function useGenerateFigurePlan(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () =>
      apiRequest<FigurePlanGenerateAcceptedResponse>(`/systems/${systemId}/figure-plans/generate`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useConfirmFigurePlan(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (planId: string) =>
      apiRequest<FigurePlanDetail>(`/figure-plans/${planId}/confirm`, {
        method: "POST",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function usePatchFigurePlan(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ planId, input }: { planId: string; input: FigurePlanPatchInput }) =>
      apiRequest<FigurePlanDetail>(`/figure-plans/${planId}`, {
        method: "PATCH",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
      // Skeleton figure_framework may have been updated by the backend sync
      queryClient.invalidateQueries({ queryKey: ["skeletons", systemId] })
      queryClient.invalidateQueries({ predicate: (query) => query.queryKey[0] === "skeleton" })
    },
  })
}

export function useUpdateFigurePlanBrief(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ planId, briefText }: { planId: string; briefText: string }) =>
      apiRequest<FigurePlanDetail>(`/figure-plans/${planId}/brief`, {
        method: "PUT",
        body: JSON.stringify({ briefText }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanKeys.list(systemId) })
    },
  })
}

export function useDeleteFigurePlan(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (planId: string) =>
      apiRequest<void>(`/figure-plans/${planId}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}

export function useTransitionFigurePlanStatus(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ planId, status }: { planId: string; status: string }) =>
      apiRequest<FigurePlanDetail>(`/figure-plans/${planId}/status`, {
        method: "PUT",
        body: JSON.stringify({ status }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: figurePlanKeys.list(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}
