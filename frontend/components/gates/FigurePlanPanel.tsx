import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import type { SystemDetail } from "../../hooks/useProjects"
import {
  useFigurePlans,
  useGenerateFigurePlan,
  useConfirmFigurePlan,
} from "../../hooks/useFigurePlan"
import { useSkeletons } from "../../hooks/useSkeletons"
import { gateTheme } from "../../styles/gate-theme"
import { ActionButton } from "../ui/ActionButton"
import { EmptyState } from "../ui/EmptyState"
import { SectionCard } from "../ui/SectionCard"
import { GateTaskStatus } from "./GateTaskStatus"
import { FigurePlanWorkbench } from "./g1/FigurePlanWorkbench"

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
  systemDetail?: SystemDetail | null
}>

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

export function FigurePlanPanel({ systemId, blockers, systemDetail }: GateContentPanelProps) {
  const { data: plans, isLoading, error } = useFigurePlans(systemId)
  const { data: skeletons } = useSkeletons(systemId)
  const generatePlan = useGenerateFigurePlan(systemId)
  const confirmPlan = useConfirmFigurePlan(systemId)

  const figurePlans = plans ?? []
  const sections = systemDetail?.sections ?? []
  const latestSkeletonId =
    skeletons?.find((s) => s.status === "confirmed")?.id ?? skeletons?.[0]?.id

  const generatePlanErrorMessage =
    generatePlan.error instanceof Error ? generatePlan.error.message : null
  const confirmPlanErrorMessage =
    confirmPlan.error instanceof Error ? confirmPlan.error.message : null

  return (
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G1" />
      <SectionCard title="图表规划" description="基于骨架图表框架管理 Figure Plan。按图表筛选、编辑简述、确认后推进至数据上传阶段。">
        {isLoading ? (
          <EmptyState text="加载规划中..." />
        ) : error ? (
          <EmptyState text={`加载规划失败：${error instanceof Error ? error.message : "未知错误"}`} style={{ color: "#fca5a5" }} />
        ) : (
          <FigurePlanWorkbench
            systemId={systemId}
            sections={sections}
            plans={figurePlans}
            skeletonId={latestSkeletonId}
          />
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
