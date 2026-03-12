import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import {
  useFigurePlans,
  useGenerateFigurePlan,
  useConfirmFigurePlan,
} from "../../hooks/useFigurePlan"
import { gateTheme } from "../../styles/gate-theme"
import { ActionButton } from "../ui/ActionButton"
import { EmptyState } from "../ui/EmptyState"
import { SectionCard } from "../ui/SectionCard"
import { StatusBadge } from "../ui/StatusBadge"
import { GateTaskStatus } from "./GateTaskStatus"

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
}>

const listStyle = { display: "flex", flexDirection: "column" as const, gap: "10px", marginTop: "12px" }

const itemCardStyle = {
  padding: "12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(15, 23, 42, 0.4)",
}

const itemHeaderStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginBottom: "4px",
}

const itemTitleStyle = { fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }
const itemDescStyle = { fontSize: "12px", color: "#94a3b8", lineHeight: 1.4 }
const errorTextStyle = { fontSize: "12px", color: "#fca5a5" }

const blockerListStyle = { display: "flex", flexDirection: "column" as const, gap: "6px", marginTop: "8px" }
const blockerItemStyle = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  fontSize: "12px",
  color: "#fca5a5",
}

function isDraftStatus(status: string): boolean {
  return status.trim().toLowerCase() === "draft"
}

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
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G1" />
      <SectionCard title="图表规划" description="管理 Figure Plan 的生成与确认。确认后可推进至数据上传阶段。">
        {isLoading ? (
          <EmptyState text="加载规划中..." />
        ) : error ? (
          <EmptyState text={`加载规划失败：${error instanceof Error ? error.message : "未知错误"}`} style={{ color: "#fca5a5" }} />
        ) : !hasPlans ? (
          <EmptyState text="尚未生成图表规划。" />
        ) : (
          <div style={listStyle}>
            {figurePlans.map((plan) => {
              const isConfirmingPlan = confirmPlan.isPending && confirmPlan.variables === plan.id

              return (
                <div key={plan.id} style={itemCardStyle}>
                  <div style={itemHeaderStyle}>
                    <div style={itemTitleStyle}>
                      图 {plan.figureNo}：{plan.title}
                    </div>
                    <StatusBadge status={plan.status} />
                  </div>
                  {plan.claimText ? <div style={itemDescStyle}>{plan.claimText}</div> : null}
                  {isDraftStatus(plan.status) ? (
                    <ActionButton
                      label={isConfirmingPlan ? "确认中..." : "确认规划"}
                      onClick={() => confirmPlan.mutate(plan.id)}
                      disabled={confirmPlan.isPending}
                      isPending={isConfirmingPlan}
                      style={{ marginTop: "8px", padding: "4px 12px" }}
                    />
                  ) : null}
                </div>
              )
            })}
          </div>
        )}
      </SectionCard>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" as const }}>
        <ActionButton
          label={generatePlan.isPending ? "生成中..." : "生成图表规划"}
          onClick={() => generatePlan.mutate()}
          disabled={generatePlan.isPending}
          isPending={generatePlan.isPending}
        />
      </div>
      {generatePlanErrorMessage ? <div style={errorTextStyle}>图表规划生成失败：{generatePlanErrorMessage}</div> : null}
      {confirmPlanErrorMessage ? <div style={errorTextStyle}>图表规划确认失败：{confirmPlanErrorMessage}</div> : null}

      {blockers.length > 0 ? (
        <SectionCard title={<span style={{ fontSize: "13px", color: "#fca5a5" }}>阻塞项 ({blockers.length})</span>}>
          <div style={blockerListStyle}>
            {blockers.map((b, i) => (
              <div key={`${b.code}-${i}`} style={blockerItemStyle}>
                <strong>{b.code}</strong>: {b.message}
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}
    </div>
  )
}
