import type { TaskEvent } from "./websocket"

export const GATE_KEYS = ["G0", "G1", "G2", "G3", "G4", "G5"] as const

export type GateKey = (typeof GATE_KEYS)[number]

type TaskPrefixMapping = Readonly<{
  gateKey: GateKey
  prefixes: readonly string[]
}>

const TASK_PREFIX_MAPPINGS: readonly TaskPrefixMapping[] = [
  { gateKey: "G1", prefixes: ["figure_plan"] },
  { gateKey: "G2", prefixes: ["analysis"] },
  { gateKey: "G3", prefixes: ["manifest"] },
  { gateKey: "G4", prefixes: ["evidence", "outline"] },
  { gateKey: "G5", prefixes: ["draft", "section_draft"] },
]

export function isGateKey(value: string | null | undefined): value is GateKey {
  return GATE_KEYS.includes(value as GateKey)
}

export function getTaskTypeFromTaskId(taskId: string | null | undefined): string | null {
  if (!taskId) {
    return null
  }

  const [workflowKey] = taskId.split(":")
  const normalized = workflowKey?.trim().toLowerCase() ?? ""
  return normalized.length > 0 ? normalized : null
}

export function getGateKeyFromTaskType(taskType: string | null | undefined): GateKey | null {
  if (!taskType) {
    return null
  }

  const normalized = taskType.trim().toLowerCase().replace(/[.-]/g, "_")
  if (!normalized) {
    return null
  }

  for (const mapping of TASK_PREFIX_MAPPINGS) {
    const matched = mapping.prefixes.some(
      (prefix) => normalized === prefix || normalized.startsWith(`${prefix}_`),
    )

    if (matched) {
      return mapping.gateKey
    }
  }

  return null
}

export function getGateKeyFromTaskEvent(event: Pick<TaskEvent, "taskId">): GateKey | null {
  return getGateKeyFromTaskType(getTaskTypeFromTaskId(event.taskId))
}
