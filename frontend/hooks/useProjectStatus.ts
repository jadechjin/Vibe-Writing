"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"

import { apiRequest } from "../lib/api"
import { deriveGateItems } from "../lib/gates"
import type { GateKey } from "../lib/gates"

export type { GateStatusItem } from "../lib/gates"
export { deriveGateItems, GATE_ORDER, countCompletedGates } from "../lib/gates"
export type { GateKey } from "../lib/gates"

// ---- Domain types ----

export type RawWorkflowEventRecord = {
  id: string
  event_type: string
  status: string
  message: string
  from_state: string | null
  to_state: string | null
  progress: number | null
  payload: Record<string, unknown>
  created_at: string
}

export type WorkflowEventRecord = {
  id: string
  eventType: string
  status: string
  message: string
  fromState: string | null
  toState: string | null
  progress: number | null
  payload: Record<string, unknown>
  createdAt: string
}

export type RawBlocker = {
  code: string
  message: string
  gate: string | null
  current_state: string | null
  required_checks: string[]
  details: Record<string, unknown>
}

export type Blocker = {
  code: string
  message: string
  gate: string | null
  currentState: string | null
  requiredChecks: string[]
  details: Record<string, unknown>
}

export type RawWorkflowSnapshot = {
  workflow_id: string
  job_id: string
  project_id: string
  system_id: string
  workflow_key: string
  current_state: string
  current_gate: string | null
  status: string
  context: Record<string, unknown>
  version: number
  started_at: string
  completed_at: string | null
  last_error: string | null
  latest_event: RawWorkflowEventRecord | null
  latest_blockers: RawBlocker[]
  events: RawWorkflowEventRecord[]
}

export type WorkflowSnapshot = {
  workflowId: string
  jobId: string
  projectId: string
  systemId: string
  workflowKey: string
  currentState: string
  currentGate: string | null
  status: string
  context: Record<string, unknown>
  version: number
  startedAt: string
  completedAt: string | null
  lastError: string | null
  latestEvent: WorkflowEventRecord | null
  latestBlockers: Blocker[]
  events: WorkflowEventRecord[]
}

export function normalizeWorkflowEventRecord(raw: RawWorkflowEventRecord): WorkflowEventRecord {
  return {
    id: raw.id,
    eventType: raw.event_type,
    status: raw.status,
    message: raw.message,
    fromState: raw.from_state,
    toState: raw.to_state,
    progress: raw.progress,
    payload: raw.payload,
    createdAt: raw.created_at,
  }
}

export function normalizeBlocker(raw: RawBlocker): Blocker {
  return {
    code: raw.code,
    message: raw.message,
    gate: raw.gate,
    currentState: raw.current_state,
    requiredChecks: raw.required_checks ?? [],
    details: raw.details ?? {},
  }
}

export function normalizeWorkflowSnapshot(raw: RawWorkflowSnapshot | null): WorkflowSnapshot | null {
  if (!raw) {
    return null
  }

  const inferredGate = resolveActiveGateFromState(raw.current_state)

  return {
    workflowId: raw.workflow_id,
    jobId: raw.job_id,
    projectId: raw.project_id,
    systemId: raw.system_id,
    workflowKey: raw.workflow_key,
    currentState: raw.current_state,
    currentGate: inferredGate ?? raw.current_gate,
    status: raw.status,
    context: raw.context ?? {},
    version: raw.version,
    startedAt: raw.started_at,
    completedAt: raw.completed_at,
    lastError: raw.last_error,
    latestEvent: raw.latest_event ? normalizeWorkflowEventRecord(raw.latest_event) : null,
    latestBlockers: (raw.latest_blockers ?? []).map(normalizeBlocker),
    events: (raw.events ?? []).map(normalizeWorkflowEventRecord),
  }
}

// ---- Gate state resolution (internal) ----

const ACTIVE_GATE_BY_STATE: Partial<Record<string, GateKey>> = {
  Draft: "G0",
  System_Defined: "G1",
  Figure_Plan_Ready: "G2",
  Data_Pending: "G2",
  Data_Uploaded: "G2",
  Analysis_Ready: "G3",
  Assets_Confirmed: "G4",
  Evidence_Matrix_Ready: "G4",
  Outline_Ready: "G5",
  Section_Drafting: "G5",
  Chapter_Review: "G5",
  Chapter_Approved: "G5",
}

function resolveActiveGateFromState(state: string | null | undefined): GateKey | null {
  if (!state) {
    return null
  }

  return ACTIVE_GATE_BY_STATE[state] ?? null
}

export function applySystemStateToSnapshot(
  snapshot: WorkflowSnapshot | null,
  systemState: string | null | undefined,
): WorkflowSnapshot | null {
  if (!snapshot) {
    return snapshot
  }

  const nextState = systemState ?? snapshot.currentState
  const nextGate = resolveActiveGateFromState(nextState)
  if (!nextGate) {
    return snapshot
  }

  if (snapshot.currentState === nextState && snapshot.currentGate === nextGate) {
    return snapshot
  }

  return {
    ...snapshot,
    currentState: nextState,
    currentGate: nextGate,
  }
}

// ---- Query keys ----

const workflowKeys = {
  snapshot: (systemId: string) => ["workflow", systemId] as const,
}

// ---- Hooks ----

export function useProjectStatus(systemId: string) {
  const query = useQuery({
    queryKey: workflowKeys.snapshot(systemId),
    queryFn: async () => normalizeWorkflowSnapshot(await apiRequest<RawWorkflowSnapshot | null>(`/systems/${systemId}/workflow`)),
    enabled: !!systemId,
    refetchInterval: 10_000,
  })

  const gateItems = deriveGateItems(query.data ?? null)

  return {
    ...query,
    snapshot: query.data ?? null,
    gateItems,
  }
}

export function useWorkflowInvalidation(systemId: string) {
  const queryClient = useQueryClient()

  return useCallback(() => {
    queryClient.invalidateQueries({ queryKey: workflowKeys.snapshot(systemId) })
  }, [queryClient, systemId])
}
