"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import type { SystemDetail } from "./useProjects"

// ---- Domain types ----

export type SystemUpdateInput = {
  title?: string
}

// ---- Query keys ----

const systemKeys = {
  detail: (systemId: string) => ["system", systemId] as const,
}

// ---- Hooks ----

export function useSystemDetail(systemId: string) {
  return useQuery({
    queryKey: systemKeys.detail(systemId),
    queryFn: () => apiRequest<SystemDetail>(`/systems/${systemId}`),
    enabled: !!systemId,
  })
}

export function useUpdateSystem(systemId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: SystemUpdateInput) =>
      apiRequest<SystemDetail>(`/systems/${systemId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: systemKeys.detail(systemId) })
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })
}
