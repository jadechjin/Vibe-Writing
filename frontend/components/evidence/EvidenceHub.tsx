import type { CSSProperties } from "react"

import { EmptyEvidenceState } from "./EmptyEvidenceState"
import { G0EvidencePanel } from "./G0EvidencePanel"
import { G1EvidencePanel } from "./G1EvidencePanel"
import { G5EvidencePanel } from "./G5EvidencePanel"
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
      description: "请先创建实验体系并确认结构骨架，证据中枢将在工作流启动后激活。",
      nextAction: "创建实验体系",
      hint: "结构骨架确认后，将自动进入 Figure Plan 阶段。",
    }
  }

  switch (gateKey) {
    case "G0":
      return {
        title: "等待结构骨架确认",
        description: "当前处于 G0 阶段，请上传模板文献并确认论文结构骨架。",
        nextAction: "确认结构骨架",
        hint: "通过 G0 后将解锁 Figure Plan 入口。",
      }
    case "G1":
      return {
        title: "图表规划与数据分析",
        description: resolveG1Description(currentState),
        nextAction: resolveG1Action(currentState),
        hint: "数据上传并完成分析后，将进入资产确认阶段。",
      }
    case "G2":
      return {
        title: "证据矩阵与提纲",
        description: "当前处于 G2 阶段，需要审核并确认 Manifest 中的全部资产状态，随后生成 Evidence Matrix 与 Outline。",
        nextAction: "等待 Manifest 确认",
        hint: "资产确认后将生成 Evidence Matrix。",
      }
    case "G3":
      return {
        title: "章节撰写与审批",
        description: "当前处于 G3 阶段，逐节生成草稿并提交审批。证据面板将呈现与当前 section 关联的 claims 与 figures。",
        hint: "所有 section 审批通过后，本章节即完成。",
      }
    default:
      return {
        title: "证据中枢",
        description: "当前门禁状态未知，请等待工作流数据同步。",
      }
  }
}

function resolveG1Description(currentState: string | null): string {
  switch (currentState) {
    case "Data_Pending":
      return "请上传实验数据与图像文件，为后续分析提供原始素材。"
    case "Data_Uploaded":
      return "数据已上传，等待系统完成自动分析。"
    case "Analysis_Ready":
      return "数据分析已完成，可推进至资产确认阶段。"
    default:
      return "当前处于 G1 阶段，请确认图表规划或上传数据。"
  }
}

function resolveG1Action(currentState: string | null): string | undefined {
  switch (currentState) {
    case "Data_Pending":
      return "上传数据文件"
    case "Data_Uploaded":
      return "等待分析完成"
    case "Analysis_Ready":
      return "推进至 G2"
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

// ---- Component ----

export function EvidenceHub({ snapshot, latestBlockers, gateKey, systemId }: EvidenceHubProps) {
  const currentState = snapshot?.currentState ?? null
  const content = resolveEvidenceContent(gateKey, currentState)

  return (
    <div style={containerStyle}>
      {gateKey === "G0" && systemId ? (
        <G0EvidencePanel systemId={systemId} />
      ) : gateKey === "G1" && systemId ? (
        <G1EvidencePanel systemId={systemId} />
      ) : gateKey === "G3" && systemId ? (
        <G5EvidencePanel systemId={systemId} />
      ) : (
        <EmptyEvidenceState
          title={content.title}
          description={content.description}
          nextAction={content.nextAction}
          hint={content.hint}
        />
      )}
    </div>
  )
}
