"use client"

import type { CSSProperties } from "react"
import type { EvidenceGapDetail } from "../../../types/g4"
import { ActionButton } from "../../ui/ActionButton"

type Props = {
  gap: EvidenceGapDetail
  onAction?: () => void
}

const gapTypeLabels: Record<string, string> = {
  missing_evidence: "缺少证据",
  missing_analysis: "缺少分析",
  weak_evidence: "证据薄弱",
  section_uncovered: "章节未覆盖",
  binding_missing: "缺少绑定",
}

const gapTypeColors: Record<string, string> = {
  missing_evidence: "#f87171",
  missing_analysis: "#fb923c",
  weak_evidence: "#fbbf24",
  section_uncovered: "#f87171",
  binding_missing: "#fb923c",
}

const severityColors: Record<string, string> = {
  blocker: "#f87171",
  warning: "#fb923c",
  info: "#94a3b8",
}

const severityLabels: Record<string, string> = {
  blocker: "阻塞",
  warning: "警告",
  info: "提示",
}

const cardStyle: CSSProperties = {
  padding: "12px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(248, 113, 113, 0.15)",
  background: "rgba(127, 29, 29, 0.08)",
}

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  flexWrap: "wrap",
}

const stageBadgeStyle: CSSProperties = {
  fontSize: "10px",
  fontWeight: 600,
  padding: "2px 8px",
  borderRadius: "4px",
  background: "rgba(148, 163, 184, 0.15)",
  color: "#cbd5e1",
}

const badgeStyle = (color: string): CSSProperties => ({
  fontSize: "10px",
  fontWeight: 600,
  padding: "2px 8px",
  borderRadius: "4px",
  background: `${color}20`,
  color,
  textTransform: "uppercase",
})

export function EvidenceGapCard({ gap, onAction }: Props) {
  const color = gapTypeColors[gap.gapType] ?? "#94a3b8"
  const severityColor = severityColors[gap.severity] ?? "#94a3b8"
  return (
    <div style={cardStyle}>
      <div style={headerStyle}>
        <span style={badgeStyle(severityColor)}>{severityLabels[gap.severity] ?? gap.severity}</span>
        <span style={stageBadgeStyle}>{gap.remediationStage}</span>
        <span style={badgeStyle(color)}>{gapTypeLabels[gap.gapType] ?? gap.gapType}</span>
        {gap.claimId ? <span style={{ fontSize: "11px", color: "#64748b" }}>{gap.claimId}</span> : null}
      </div>
      <div style={{ fontSize: "12px", color: "#e2e8f0", marginTop: "6px" }}>{gap.message}</div>
      <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>{gap.suggestedAction}</div>
      {gap.remediationHint ? (
        <div style={{ fontSize: "11px", color: "#cbd5e1", marginTop: "4px", fontStyle: "italic" }}>{gap.remediationHint}</div>
      ) : null}
      {onAction ? (
        <div style={{ marginTop: "8px" }}>
          <ActionButton label="处理" onClick={onAction} variant="secondary" style={{ padding: "4px 12px", fontSize: "11px" }} />
        </div>
      ) : null}
    </div>
  )
}
