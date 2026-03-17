"use client"

import type { CSSProperties } from "react"
import type { OutlineNodeData } from "../../../types/g4"

type Props = {
  node: OutlineNodeData
}

const nodeTypeLabels: Record<string, string> = {
  background: "背景",
  method: "方法",
  result: "结果",
  summary: "总结",
}

const nodeTypeColors: Record<string, string> = {
  background: "#93c5fd",
  method: "#c4b5fd",
  result: "#86efac",
  summary: "#fde68a",
}

const strengthColors: Record<string, string> = {
  strong: "#86efac",
  medium: "#fde68a",
  weak: "#fca5a5",
}

const nodeStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  background: "rgba(15, 23, 42, 0.25)",
}

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
}

const labelBadge = (color: string): CSSProperties => ({
  fontSize: "10px",
  fontWeight: 600,
  padding: "2px 8px",
  borderRadius: "4px",
  background: `${color}20`,
  color,
  textTransform: "uppercase",
})

export function OutlineNode({ node }: Props) {
  const color = nodeTypeColors[node.nodeType] ?? "#94a3b8"
  const strengthColor = strengthColors[node.evidenceStrength] ?? "#94a3b8"

  return (
    <div style={nodeStyle}>
      <div style={headerStyle}>
        <span style={labelBadge(color)}>{nodeTypeLabels[node.nodeType] ?? node.nodeType}</span>
        <span style={{ ...labelBadge(strengthColor), fontSize: "9px" }}>{node.evidenceStrength}</span>
        <span style={{ fontSize: "11px", color: "#64748b" }}>{(node.claimIds ?? []).length} claims</span>
      </div>
      <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "4px" }}>
        {(node.claimIds ?? []).join(", ")}
      </div>
    </div>
  )
}
