import { ApiError } from "../../../lib/api"

export type G4IssueAction =
  | { id: "focus-claims"; label: string; variant?: "primary" | "secondary" | "danger" }
  | { id: "focus-outline"; label: string; variant?: "primary" | "secondary" | "danger" }
  | { id: "focus-readiness"; label: string; variant?: "primary" | "secondary" | "danger" }
  | { id: "force-regenerate"; label: string; variant?: "primary" | "secondary" | "danger" }

export type G4IssueDetail = {
  title: string
  summary: string
  code: string
  metrics: Array<{ label: string; value: string }>
  impactItems: string[]
  sectionsAffected: string[]
  actions: G4IssueAction[]
}

function getNumber(details: Record<string, unknown>, key: string): number {
  const value = details[key]
  return typeof value === "number" ? value : 0
}

function getStringArray(details: Record<string, unknown>, key: string): string[] {
  const value = details[key]
  if (!Array.isArray(value)) return []
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
}

export function resolveG4IssueDetail(error: unknown): G4IssueDetail | null {
  if (!(error instanceof ApiError)) return null

  const isEvidenceConflict =
    error.code === "evidence_matrix_regeneration_conflict" ||
    (error.status === 409 && error.message.includes("Cannot regenerate evidence matrix"))
  if (!isEvidenceConflict) return null

  const approvedLatestClaimCount = getNumber(error.details, "approved_latest_claim_count")
  const confirmedOutlineCount = getNumber(error.details, "confirmed_outline_count")
  const sectionsAffected = getStringArray(error.details, "sections_affected")

  return {
    title: "重建冲突详情",
    summary: "当前系统已经存在最新 Approved Claims 或已确认 Outline，直接重建会使这些后续产物失效，需要先审阅影响范围或显式确认强制重建。",
    code: error.code ?? "evidence_matrix_regeneration_conflict",
    metrics: [
      { label: "Approved Claims", value: String(approvedLatestClaimCount) },
      { label: "Confirmed Outline", value: String(confirmedOutlineCount) },
    ],
    impactItems: [
      approvedLatestClaimCount > 0 ? `有 ${approvedLatestClaimCount} 条最新 Approved Claims 会失去当前审批语义。` : "当前没有 Approved Claims 会被覆盖。",
      confirmedOutlineCount > 0 ? `有 ${confirmedOutlineCount} 个已确认 Outline 会失效并需要重新确认。` : "当前没有已确认 Outline 会失效。",
    ],
    sectionsAffected,
    actions: [
      { id: "focus-claims", label: "去 Claims", variant: "secondary" },
      { id: "focus-outline", label: "去 Outline", variant: "secondary" },
      { id: "focus-readiness", label: "去推进条件", variant: "secondary" },
      { id: "force-regenerate", label: "确认后强制重建", variant: "danger" },
    ],
  }
}
