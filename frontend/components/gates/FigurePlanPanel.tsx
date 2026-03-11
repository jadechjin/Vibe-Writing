import type { CSSProperties } from "react"

import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import {
  useFigurePlans,
  useGenerateFigurePlan,
  useConfirmFigurePlan,
} from "../../hooks/useFigurePlan"
import { GateTaskStatus } from "./GateTaskStatus"

// ---- Props ----

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
}>

// ---- Styles ----

const panelStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
}

const sectionCardStyle: CSSProperties = {
  padding: "16px",
  borderRadius: "14px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(30, 41, 59, 0.38)",
}

const titleStyle: CSSProperties = {
  fontSize: "15px",
  fontWeight: 700,
  color: "#f8fafc",
  marginBottom: "8px",
}

const descStyle: CSSProperties = {
  fontSize: "13px",
  lineHeight: 1.6,
  color: "#94a3b8",
}

const blockerListStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  marginTop: "8px",
}

const blockerItemStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  fontSize: "12px",
  color: "#fca5a5",
}

const actionBtnStyle: CSSProperties = {
  padding: "8px 18px",
  borderRadius: "10px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "13px",
  fontWeight: 600,
  color: "#fb923c",
  cursor: "pointer",
  alignSelf: "flex-start",
}

const listStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "10px",
  marginTop: "12px",
}

const itemCardStyle: CSSProperties = {
  padding: "12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(15, 23, 42, 0.4)",
}

const itemHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "4px",
}

const itemTitleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#e2e8f0",
}

const statusBadgeStyle: CSSProperties = {
  fontSize: "10px",
  padding: "2px 6px",
  borderRadius: "4px",
  background: "rgba(249, 115, 22, 0.1)",
  color: "#fb923c",
  fontWeight: 600,
}

const itemDescStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
  lineHeight: 1.4,
}

const emptyStateStyle: CSSProperties = {
  padding: "20px",
  textAlign: "center",
  color: "#64748b",
  fontSize: "13px",
  fontStyle: "italic",
}

const errorTextStyle: CSSProperties = {
  fontSize: "12px",
  color: "#fca5a5",
}

function isDraftStatus(status: string): boolean {
  return status.trim().toLowerCase() === "draft"
}

// ---- Component ----

export function FigurePlanPanel({ systemId, blockers }: GateContentPanelProps) {
  const { data: plans, isLoading, error } = useFigurePlans(systemId)
  const generatePlan = useGenerateFigurePlan(systemId)
  const confirmPlan = useConfirmFigurePlan(systemId)

  const figurePlans = plans ?? []
  const hasPlans = figurePlans.length > 0
  const generatePlanErrorMessage =
    generatePlan.error instanceof Error ? generatePlan.error.message : null
  const confirmPlanErrorMessage =
    confirmPlan.error instanceof Error ? confirmPlan.error.message : null

  return (
    <div style={panelStyle}>
      <GateTaskStatus systemId={systemId} gateKey="G1" />
      <div style={sectionCardStyle}>
        <div style={titleStyle}>Figure Plan</div>
        <div style={descStyle}>
          管理 Figure Plan 的生成与确认。确认后可推进至数据上传阶段。
        </div>

        {isLoading ? (
          <div style={emptyStateStyle}>Loading plans...</div>
        ) : error ? (
          <div style={{ ...emptyStateStyle, color: "#fca5a5" }}>
            Error loading plans: {error instanceof Error ? error.message : "Unknown error"}
          </div>
        ) : !hasPlans ? (
          <div style={emptyStateStyle}>No figure plans generated yet.</div>
        ) : (
          <div style={listStyle}>
            {figurePlans.map((plan) => {
              const isConfirmingPlan = confirmPlan.isPending && confirmPlan.variables === plan.id

              return (
                <div key={plan.id} style={itemCardStyle}>
                  <div style={itemHeaderStyle}>
                    <div style={itemTitleStyle}>
                      Figure {plan.figureNo}: {plan.title}
                    </div>
                    <div style={statusBadgeStyle}>{plan.status}</div>
                  </div>
                  {plan.claimText ? <div style={itemDescStyle}>{plan.claimText}</div> : null}
                  {isDraftStatus(plan.status) ? (
                    <button
                      type="button"
                      style={{ ...actionBtnStyle, marginTop: "8px", padding: "4px 12px" }}
                      onClick={() => confirmPlan.mutate(plan.id)}
                      disabled={confirmPlan.isPending}
                    >
                      {isConfirmingPlan ? "Confirming..." : "Confirm Plan"}
                    </button>
                  ) : null}
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" as const }}>
        <button
          type="button"
          style={actionBtnStyle}
          onClick={() => generatePlan.mutate()}
          disabled={generatePlan.isPending}
        >
          {generatePlan.isPending ? "Generating..." : "Generate Figure Plan"}
        </button>
      </div>
      {generatePlanErrorMessage ? <div style={errorTextStyle}>Figure plan generation failed: {generatePlanErrorMessage}</div> : null}
      {confirmPlanErrorMessage ? <div style={errorTextStyle}>Figure plan confirmation failed: {confirmPlanErrorMessage}</div> : null}

      {blockers.length > 0 ? (
        <div style={sectionCardStyle}>
          <div style={{ ...titleStyle, fontSize: "13px", color: "#fca5a5" }}>
            Blockers ({blockers.length})
          </div>
          <div style={blockerListStyle}>
            {blockers.map((b, i) => (
              <div key={`${b.code}-${i}`} style={blockerItemStyle}>
                <strong>{b.code}</strong>: {b.message}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
