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
  createdAt: string
  updatedAt: string
}

export type FigurePlanGenerateAcceptedResponse = {
  handle: JobHandle
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
