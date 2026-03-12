import type { CSSProperties, ReactNode } from "react"

import { WorkflowPanel } from "../drafting/WorkflowPanel"
import { SystemDefinitionForm } from "./SystemDefinitionForm"
import { FigurePlanPanel } from "./FigurePlanPanel"
import { AnalysisPanel } from "./AnalysisPanel"
import { ManifestPanel } from "./ManifestPanel"
import { EvidenceMatrixPanel } from "./EvidenceMatrixPanel"
import { DraftPanel } from "./DraftPanel"
import type { GateKey } from "../../lib/gateMapping"
import type {
  WorkflowSnapshot,
  Blocker,
  WorkflowEventRecord,
} from "../../hooks/useProjectStatus"
import type { SystemDetail } from "../../hooks/useProjects"
import type { SystemUpdateInput } from "../../hooks/useSystem"

// ---- Props ----

export type GatePanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  gateKey: string | null
  selectedGate?: GateKey | null
  gateVisualState: string
  latestBlockers: Blocker[]
  latestEvent: WorkflowEventRecord | null
  systemName?: string
  projectTitle?: string
  systemDetail?: SystemDetail | null
  onUpdateSystem?: (data: SystemUpdateInput) => void
  isUpdating?: boolean
  systemId?: string
}>

// ---- Gate-to-workbench content mapping ----

type WorkbenchContent = {
  title: string
  description: string
  actionLabel?: string
  actionHint?: string
}

function resolveWorkbenchContent(
  gateKey: string | null,
  gateVisualState: string,
  currentState: string | null,
): WorkbenchContent {
  if (!gateKey || gateVisualState === "neutral") {
    return {
      title: "体系定义",
      description: "请先创建实验体系，工作区将在体系初始化后展示 gate 对应的操作面板。",
      actionLabel: "创建实验体系",
    }
  }

  if (gateVisualState === "locked") {
    return {
      title: "门禁已锁定",
      description: "当前 gate 尚未解锁，请先完成前置阶段的全部要求。",
      actionHint: "等待前置门禁通过后自动解锁。",
    }
  }

  switch (gateKey) {
    case "G0":
      return {
        title: "体系定义",
        description: "填写并确认实验体系定义，包括研究目标、技术路线与预期产出。确认后点击推进至 G1。",
        actionLabel: "推进门禁",
        actionHint: "确认体系定义后，系统将评审 G0 并尝试推进。",
      }
    case "G1":
      return {
        title: "图表规划",
        description: "等待系统生成图表规划。图表规划将规划本章节全部图表的类型、数据需求与预期呈现。",
        actionLabel: "等待图表规划生成",
        actionHint: "图表规划确认后可推进至数据上传阶段。",
      }
    case "G2":
      return resolveG2Workbench(currentState)
    case "G3":
      return {
        title: "资产确认",
        description: "审核 Manifest 中的全部资产状态，确认图表、数据文件与分析结果均已就位。",
        actionLabel: "确认 Manifest",
        actionHint: "全部资产确认后将触发证据矩阵生成。",
      }
    case "G4":
      return resolveG4Workbench(currentState)
    case "G5":
      return resolveG5Workbench(currentState)
    default:
      return {
        title: "未知门禁",
        description: "当前 gate 状态未知，请等待工作流数据同步。",
      }
  }
}

function resolveG2Workbench(currentState: string | null): WorkbenchContent {
  switch (currentState) {
    case "Data_Pending":
      return {
        title: "等待上传",
        description: "请上传实验原始数据与图像文件。系统将根据图表规划进行自动关联与分析。",
        actionLabel: "上传数据文件",
      }
    case "Data_Uploaded":
      return {
        title: "分析进行中",
        description: "数据已上传，正在等待系统完成自动分析。分析任务可在底部状态栏中跟踪。",
        actionHint: "分析完成后可推进至 G3。",
      }
    case "Analysis_Ready":
      return {
        title: "分析完成",
        description: "数据分析已完成，可推进至资产确认阶段。",
        actionLabel: "推进门禁",
      }
    default:
      return {
        title: "数据与分析",
        description: "当前处于数据与分析阶段，请上传数据或等待分析完成。",
      }
  }
}

function resolveG4Workbench(currentState: string | null): WorkbenchContent {
  switch (currentState) {
    case "Evidence_Matrix_Ready":
      return {
        title: "证据矩阵就绪",
        description: "证据矩阵已生成。请审核 claim-figure-analysis 关联，确认后系统将生成提纲。",
        actionLabel: "确认证据矩阵",
      }
    case "Outline_Ready":
      return {
        title: "提纲就绪",
        description: "提纲已生成，包含章节结构与各 section 的主题规划。确认后推进至草稿撰写阶段。",
        actionLabel: "推进门禁",
      }
    default:
      return {
        title: "证据与提纲",
        description: "等待证据矩阵与提纲生成并确认。",
        actionHint: "此阶段完成后进入章节撰写。",
      }
  }
}

function resolveG5Workbench(currentState: string | null): WorkbenchContent {
  switch (currentState) {
    case "Section_Drafting":
      return {
        title: "草稿生成中",
        description: "逐节生成草稿中。当前 section 的草稿将基于已批准的 claims 与 Evidence Matrix 生成。",
        actionHint: "草稿生成后可进入审批流程。",
      }
    case "Chapter_Review":
      return {
        title: "等待审批",
        description: "章节草稿已完成，等待审批。审批通过后本章节即完成。",
        actionLabel: "提交审批",
      }
    case "Chapter_Approved":
      return {
        title: "章节已通过",
        description: "本章节已通过审批，实验体系闭环完成。",
      }
    default:
      return {
        title: "章节撰写",
        description: "当前处于章节撰写与审批阶段。",
      }
  }
}

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "18px",
}

const headerCardStyle: CSSProperties = {
  padding: "20px",
  borderRadius: "16px",
  border: "1px dashed rgba(249, 115, 22, 0.35)",
  background: "rgba(30, 41, 59, 0.38)",
  display: "flex",
  flexDirection: "column",
  gap: "12px",
  textAlign: "center",
}

const headerTitleStyle: CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  color: "#f8fafc",
}

const headerDescStyle: CSSProperties = {
  fontSize: "14px",
  lineHeight: 1.6,
  color: "#94a3b8",
}

const actionLabelStyle: CSSProperties = {
  display: "inline-block",
  padding: "8px 18px",
  borderRadius: "12px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "13px",
  fontWeight: 600,
  color: "#fb923c",
}

const actionHintStyle: CSSProperties = {
  fontSize: "12px",
  color: "#64748b",
  fontStyle: "italic",
}

const contextBarStyle: CSSProperties = {
  display: "flex",
  gap: "16px",
  flexWrap: "wrap",
  fontSize: "12px",
  color: "#64748b",
}

const contextItemStyle: CSSProperties = {
  display: "flex",
  gap: "4px",
}

const contextLabelStyle: CSSProperties = {
  fontWeight: 600,
  color: "#94a3b8",
}

// ---- Component ----

export function GatePanel({
  snapshot,
  gateKey,
  selectedGate,
  gateVisualState,
  latestBlockers,
  latestEvent,
  systemName,
  projectTitle,
  systemDetail,
  onUpdateSystem,
  isUpdating,
  systemId,
}: GatePanelProps) {
  const effectiveGateKey = selectedGate ?? gateKey
  const currentState = snapshot?.currentState ?? null
  const content = resolveWorkbenchContent(effectiveGateKey, gateVisualState, currentState)

  const showG0Form = effectiveGateKey === "G0" && (gateVisualState === "active" || gateVisualState === "passed")
  const g0ReadOnly = gateVisualState === "passed"

  const systemIdStr = systemId ?? snapshot?.systemId ?? ""

  function resolveGatePanel(): ReactNode | null {
    if (!effectiveGateKey || gateVisualState === "locked" || gateVisualState === "neutral") return null
    if (effectiveGateKey === "G0") return null // handled by SystemDefinitionForm

    const panelProps = { snapshot, blockers: latestBlockers, systemId: systemIdStr, systemDetail: systemDetail ?? null }

    switch (effectiveGateKey) {
      case "G1": return <FigurePlanPanel {...panelProps} />
      case "G2": return <AnalysisPanel {...panelProps} />
      case "G3": return <ManifestPanel {...panelProps} />
      case "G4": return <EvidenceMatrixPanel {...panelProps} />
      case "G5": return <DraftPanel {...panelProps} />
      default: return null
    }
  }

  const gatePanel = resolveGatePanel()

  return (
    <div style={containerStyle}>
      {/* Context bar */}
      {(systemName ?? projectTitle) ? (
        <div style={contextBarStyle}>
          {projectTitle ? (
            <div style={contextItemStyle}>
              <span style={contextLabelStyle}>项目：</span>
              <span>{projectTitle}</span>
            </div>
          ) : null}
          {systemName ? (
            <div style={contextItemStyle}>
              <span style={contextLabelStyle}>体系：</span>
              <span>{systemName}</span>
            </div>
          ) : null}
          {effectiveGateKey ? (
            <div style={contextItemStyle}>
              <span style={contextLabelStyle}>门禁：</span>
              <span>{effectiveGateKey} ({gateVisualState})</span>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* G0 form, gate panel, or workbench empty state */}
      {showG0Form && onUpdateSystem ? (
        <SystemDefinitionForm
          initialData={systemDetail ?? null}
          blockers={g0ReadOnly ? [] : latestBlockers}
          onSave={onUpdateSystem}
          isReadOnly={g0ReadOnly}
          isUpdating={isUpdating}
        />
      ) : gatePanel ? (
        gatePanel
      ) : (
        <div style={headerCardStyle}>
          <div style={headerTitleStyle}>{content.title}</div>
          <div style={headerDescStyle}>{content.description}</div>
          {content.actionLabel ? (
            <div style={actionLabelStyle}>{content.actionLabel}</div>
          ) : null}
          {content.actionHint ? (
            <div style={actionHintStyle}>{content.actionHint}</div>
          ) : null}
        </div>
      )}

      {/* Workflow panel */}
      <WorkflowPanel
        snapshot={snapshot}
        latestBlockers={latestBlockers}
        latestEvent={latestEvent}
      />
    </div>
  )
}
