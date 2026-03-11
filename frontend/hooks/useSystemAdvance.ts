"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"

import { apiRequest } from "../lib/api"
import {
  normalizeBlocker,
  normalizeWorkflowSnapshot,
  type RawWorkflowSnapshot,
  type RawBlocker,
  type WorkflowSnapshot,
  type Blocker,
} from "./useProjectStatus"

// ---- Domain types ----

export type RawJobHandle = {
  workflow_id: string | null
  job_id: string
  status: string
}

export type JobHandle = {
  workflowId: string | null
  jobId: string
  status: string
}

export type RawAdvanceResponse = {
  outcome: "accepted" | "blocked"
  gate: string
  currentState?: string | null
  fromState?: string | null
  toState?: string | null
  current_state?: string | null
  from_state?: string | null
  to_state?: string | null
  blockers: RawBlocker[]
  handle: RawJobHandle | null
  snapshot: RawWorkflowSnapshot
}

export type AdvanceResponse = {
  outcome: "accepted" | "blocked"
  gate: string
  currentState: string | null
  fromState: string | null
  toState: string | null
  blockers: Blocker[]
  handle: JobHandle | null
  snapshot: WorkflowSnapshot | null
}

function normalizeJobHandle(raw: RawJobHandle): JobHandle {
  return {
    workflowId: raw.workflow_id,
    jobId: raw.job_id,
    status: raw.status,
  }
}

function normalizeAdvanceResponse(raw: RawAdvanceResponse): AdvanceResponse {
  return {
    outcome: raw.outcome,
    gate: raw.gate,
    currentState: raw.currentState ?? raw.current_state ?? null,
    fromState: raw.fromState ?? raw.from_state ?? null,
    toState: raw.toState ?? raw.to_state ?? null,
    blockers: (raw.blockers ?? []).map(normalizeBlocker),
    handle: raw.handle ? normalizeJobHandle(raw.handle) : null,
    snapshot: normalizeWorkflowSnapshot(raw.snapshot),
  }
}

// ---- Hook ----

export function useSystemAdvance(systemId: string) {
  const queryClient = useQueryClient()

  const mutation = useMutation({
    mutationFn: async () =>
      normalizeAdvanceResponse(
        await apiRequest<RawAdvanceResponse>(`/systems/${systemId}/advance`, {
          method: "POST",
        }),
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflow", systemId] })
    },
  })

  return {
    advance: mutation.mutate,
    advanceAsync: mutation.mutateAsync,
    isPending: mutation.isPending,
    isError: mutation.isError,
    error: mutation.error,
    data: mutation.data ?? null,
    reset: mutation.reset,
  }
}
