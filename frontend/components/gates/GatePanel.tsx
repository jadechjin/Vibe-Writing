import type { CSSProperties, ReactNode } from "react"

import { WorkflowPanel } from "../drafting/WorkflowPanel"
import { G0Workbench } from "./G0Workbench"
import { G1Panel } from "./G1Panel"
import { G2Panel } from "./G2Panel"
import { DraftPanel } from "./DraftPanel"
import type { GateKey } from "../../lib/gateMapping"
import type {
  WorkflowSnapshot,
  Blocker,
  WorkflowEventRecord,
} from "../../hooks/useProjectStatus"
import type { SystemDetail } from "../../hooks/useProjects"

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
        description: "整理模板文献并确认结构骨架。完成后点击推进至 G1。",
        actionLabel: "推进门禁",
        actionHint: "结构骨架确认后，系统将评审 G0 并尝试推进。",
      }
    case "G1":
      return resolveG1Workbench(currentState)
    case "G2":
      return resolveG2Workbench(currentState)
    case "G3":
      return resolveG3Workbench(currentState)
    default:
      return {
        title: "未知门禁",
        description: "当前 gate 状态未知，请等待工作流数据同步。",
      }
  }
}

function resolveG1Workbench(currentState: string | null): WorkbenchContent {
  switch (currentState) {
    case "Data_Pending":
    case "Data_Uploaded":
      return {
        title: "数据与分析",
        description: "请上传实验原始数据与图像文件。系统将根据图表规划进行自动关联与分析。",
        actionLabel: "上传数据文件",
      }
    case "Analysis_Ready":
      return {
        title: "分析完成",
        description: "数据分析已完成，可推进至资产确认阶段。",
        actionLabel: "推进门禁",
      }
    default:
      return {
        title: "图表规划",
        description: "基于骨架结构规划全部图表。按章节浏览图表任务，编辑简述并确认后推进至数据上传阶段。",
        actionLabel: "推进门禁",
        actionHint: "全部图表规划确认后可推进至数据上传阶段。",
      }
  }
}

function resolveG2Workbench(currentState: string | null): WorkbenchContent {
  switch (currentState) {
    case "Assets_Confirmed":
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
        title: "资产确认",
        description: "审核 Manifest 中的全部资产状态，确认图表、数据文件与分析结果均已就位。",
        actionLabel: "确认 Manifest",
        actionHint: "全部资产确认后将触发证据矩阵生成。",
      }
  }
}

function resolveG3Workbench(currentState: string | null): WorkbenchContent {
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

const retroactiveBannerStyle: CSSProperties = {
  padding: "12px 16px",
  borderRadius: "12px",
  border: "1px solid rgba(251, 191, 36, 0.4)",
  background: "rgba(120, 53, 15, 0.18)",
  fontSize: "13px",
  color: "#fbbf24",
  fontWeight: 500,
}

const lockedPlaceholderStyle: CSSProperties = {
  padding: "24px 20px",
  borderRadius: "16px",
  border: "1px dashed rgba(120, 139, 165, 0.35)",
  background: "rgba(15, 23, 42, 0.5)",
  textAlign: "center",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
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
  systemId,
}: GatePanelProps) {
  const effectiveGateKey = selectedGate ?? gateKey
  const currentState = snapshot?.currentState ?? null
  const content = resolveWorkbenchContent(effectiveGateKey, gateVisualState, currentState)

  const isRetroactive = selectedGate != null && selectedGate !== gateKey && gateVisualState === "passed"
  const isLockedView = gateVisualState === "locked"

  const showG0Workbench = effectiveGateKey === "G0" && (gateVisualState === "active" || gateVisualState === "passed")
  const g0ReadOnly = false // passed gates are editable in retroactive mode

  const systemIdStr = systemId ?? snapshot?.systemId ?? ""

  function resolveGatePanel(): ReactNode | null {
    if (!effectiveGateKey || gateVisualState === "neutral") return null

    if (isLockedView) {
      return (
        <div style={lockedPlaceholderStyle}>
          <div style={{ fontSize: "15px", fontWeight: 700, color: "#8da2bf" }}>
            {content.title}
          </div>
          <div style={{ fontSize: "13px", color: "#64748b" }}>
            {content.description}
          </div>
        </div>
      )
    }

    if (effectiveGateKey === "G0") return null // handled by G0Workbench

    const panelProps = { snapshot, blockers: latestBlockers, systemId: systemIdStr, systemDetail: systemDetail ?? null }

    switch (effectiveGateKey) {
      case "G1": return <G1Panel {...panelProps} />
      case "G2": return <G2Panel {...panelProps} />
      case "G3": return <DraftPanel {...panelProps} />
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

      {/* Retroactive warning banner */}
      {isRetroactive ? (
        <div style={retroactiveBannerStyle}>
          您正在查看已通过的门禁，修改可能影响下游阶段
        </div>
      ) : null}

      {/* G0 workbench, gate panel, or workbench empty state */}
      {showG0Workbench ? (
        <G0Workbench
          systemId={systemIdStr}
          isReadOnly={g0ReadOnly}
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
