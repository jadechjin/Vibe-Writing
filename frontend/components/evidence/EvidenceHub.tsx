import type { CSSProperties } from "react"

import { EmptyEvidenceState } from "./EmptyEvidenceState"
import { G0EvidencePanel } from "./G0EvidencePanel"
import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"

// ---- Props ----

export type EvidenceHubProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  latestBlockers: Blocker[]
  gateKey: string | null
  systemId?: string
}>

// ---- Gate-to-evidence content mapping ----

type EvidenceContent = {
  title: string
  description: string
  nextAction?: string
  hint?: string
}

function resolveEvidenceContent(
  gateKey: string | null,
  currentState: string | null,
): EvidenceContent {
  if (!gateKey) {
    return {
      title: "等待体系初始化",
      description: "请先创建实验体系并完成体系定义，证据中枢将在工作流启动后激活。",
      nextAction: "创建实验体系",
      hint: "体系定义完成后，将自动进入 Figure Plan 阶段。",
    }
  }

  switch (gateKey) {
    case "G0":
      return {
        title: "等待体系定义",
        description: "当前处于 G0 阶段，请完善实验体系基本信息，包括研究目标、实验方案与预期产出。",
        nextAction: "完善体系定义",
        hint: "通过 G0 后将解锁 Figure Plan 入口。",
      }
    case "G1":
      return {
        title: "Figure Plan 准备中",
        description: "当前处于 G1 阶段，需要生成并确认 Figure Plan，确定图表规划与数据需求。",
        nextAction: "等待 Figure Plan 生成",
        hint: "Figure Plan 确认后，将进入数据上传与分析阶段。",
      }
    case "G2":
      return {
        title: "数据与分析",
        description: resolveG2Description(currentState),
        nextAction: resolveG2Action(currentState),
        hint: "数据上传并完成分析后，将进入资产确认阶段。",
      }
    case "G3":
      return {
        title: "资产确认中",
        description: "当前处于 G3 阶段，需要审核并确认 Manifest 中的全部资产状态。",
        nextAction: "等待 Manifest 确认",
        hint: "资产确认后将生成 Evidence Matrix。",
      }
    case "G4":
      return {
        title: "证据矩阵与提纲",
        description: "当前处于 G4 阶段，Evidence Matrix 与 Outline 生成中或等待确认。",
        nextAction: "等待 Evidence Matrix 就绪",
        hint: "此阶段完成后，证据中枢将展示完整的 claim-figure-analysis 关联面板。",
      }
    case "G5":
      return {
        title: "章节撰写与审批",
        description: "当前处于 G5 阶段，逐节生成草稿并提交审批。证据面板将呈现与当前 section 关联的 claims 与 figures。",
        hint: "所有 section 审批通过后，本章节即完成。",
      }
    default:
      return {
        title: "证据中枢",
        description: "当前门禁状态未知，请等待工作流数据同步。",
      }
  }
}

function resolveG2Description(currentState: string | null): string {
  switch (currentState) {
    case "Data_Pending":
      return "请上传实验数据与图像文件，为后续分析提供原始素材。"
    case "Data_Uploaded":
      return "数据已上传，等待系统完成自动分析。"
    case "Analysis_Ready":
      return "数据分析已完成，可推进至资产确认阶段。"
    default:
      return "当前处于 G2 阶段，请上传数据或等待分析完成。"
  }
}

function resolveG2Action(currentState: string | null): string | undefined {
  switch (currentState) {
    case "Data_Pending":
      return "上传数据文件"
    case "Data_Uploaded":
      return "等待分析完成"
    case "Analysis_Ready":
      return "推进至 G3"
    default:
      return "等待数据处理"
  }
}

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
}

const blockerSectionStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  padding: "14px 16px",
  borderRadius: "14px",
  border: "1px solid rgba(248, 113, 113, 0.25)",
  background: "rgba(127, 29, 29, 0.1)",
}

const blockerTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "#fca5a5",
}

const blockerItemStyle: CSSProperties = {
  fontSize: "13px",
  color: "#fecaca",
  lineHeight: 1.5,
}

const blockerCodeStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "#f87171",
  marginRight: "6px",
}

// ---- Component ----

export function EvidenceHub({ snapshot, latestBlockers, gateKey, systemId }: EvidenceHubProps) {
  const currentState = snapshot?.currentState ?? null
  const content = resolveEvidenceContent(gateKey, currentState)

  return (
    <div style={containerStyle}>
      {gateKey === "G0" && systemId ? (
        <G0EvidencePanel systemId={systemId} />
      ) : (
        <EmptyEvidenceState
          title={content.title}
          description={content.description}
          nextAction={content.nextAction}
          hint={content.hint}
        />
      )}

      {latestBlockers.length > 0 ? (
        <div style={blockerSectionStyle}>
          <div style={blockerTitleStyle}>当前阻塞项</div>
          {latestBlockers.map((blocker, idx) => (
            <div key={`${blocker.code}-${idx}`} style={blockerItemStyle}>
              <span style={blockerCodeStyle}>[{blocker.code}]</span>
              {blocker.message}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
