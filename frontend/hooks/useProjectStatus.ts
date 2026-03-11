"use client"

import { useQuery, useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"

import { apiRequest } from "../lib/api"
import type { GateVisualStatus } from "../components/layout/GateNav"

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

// ---- Gate key constants ----

export const GATE_ORDER = ["G0", "G1", "G2", "G3", "G4", "G5"] as const
export type GateKey = (typeof GATE_ORDER)[number]

const GATE_STATE_MAP: Record<GateKey, string[]> = {
  G0: ["System_Defined"],
  G1: ["Figure_Plan_Ready"],
  G2: ["Data_Pending", "Data_Uploaded", "Analysis_Ready"],
  G3: ["Assets_Confirmed"],
  G4: ["Evidence_Matrix_Ready", "Outline_Ready"],
  G5: ["Section_Drafting", "Chapter_Review", "Chapter_Approved"],
}

const GATE_TITLES: Record<GateKey, string> = {
  G0: "体系定义",
  G1: "Figure Plan",
  G2: "数据与分析",
  G3: "资产确认",
  G4: "证据与提纲",
  G5: "章节审批",
}

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

function resolveGateStatus(
  gateKey: GateKey,
  currentGate: string | null,
  currentState: string,
): GateVisualStatus {
  const gateIndex = GATE_ORDER.indexOf(gateKey)
  const activeIndex = currentGate ? GATE_ORDER.indexOf(currentGate as GateKey) : -1

  if (activeIndex < 0) {
    return gateIndex === 0 ? "active" : "locked"
  }

  if (gateIndex < activeIndex) {
    return "passed"
  }

  if (gateIndex === activeIndex) {
    return "active"
  }

  return "locked"
}

export type GateStatusItem = {
  key: string
  label: string
  title: string
  summary: string
  state: GateVisualStatus
}

export function deriveGateItems(snapshot: WorkflowSnapshot | null): GateStatusItem[] {
  if (!snapshot) {
    return GATE_ORDER.map((key) => ({
      key,
      label: key,
      title: GATE_TITLES[key],
      summary: "等待项目与实验体系上下文注入。",
      state: "neutral" as GateVisualStatus,
    }))
  }

  return GATE_ORDER.map((key) => {
    const status = resolveGateStatus(key, snapshot.currentGate, snapshot.currentState)

    let summary: string
    switch (status) {
      case "passed":
        summary = "已通过。"
        break
      case "active":
        summary = `当前状态: ${snapshot.currentState}`
        break
      case "locked":
        summary = "等待前置门禁通过。"
        break
      default:
        summary = "等待 gate 状态数据接入。"
    }

    return {
      key,
      label: key,
      title: GATE_TITLES[key],
      summary,
      state: status,
    }
  })
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
