import type { GateVisualStatus } from "../components/layout/GateNav"
import type { WorkflowSnapshot } from "../hooks/useProjectStatus"

export const GATE_ORDER = ["G0", "G1", "G2", "G3", "G4", "G5"] as const
export type GateKey = (typeof GATE_ORDER)[number]

const GATE_TITLES: Record<GateKey, string> = {
  G0: "体系定义",
  G1: "Figure Plan",
  G2: "数据与分析",
  G3: "资产确认",
  G4: "证据与提纲",
  G5: "章节审批",
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

export function countCompletedGates(snapshot: WorkflowSnapshot | null): number {
  if (!snapshot) return 0
  return deriveGateItems(snapshot).filter((g) => g.state === "passed").length
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

export function countCompletedGatesFromStatus(status: string): number {
  if (status === "Chapter_Approved") return GATE_ORDER.length
  const gate = ACTIVE_GATE_BY_STATE[status]
  if (!gate) return 0
  return GATE_ORDER.indexOf(gate)
}
