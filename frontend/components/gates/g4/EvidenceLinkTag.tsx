"use client"

import type { CSSProperties } from "react"

type Props = {
  assetName: string
  qcStatus?: string
  strength?: string
}

const strengthColors: Record<string, string> = {
  strong: "#86efac",
  medium: "#fde68a",
  weak: "#fca5a5",
}

const tagStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "4px",
  padding: "2px 8px",
  borderRadius: "6px",
  fontSize: "11px",
  fontWeight: 500,
  background: "rgba(15, 23, 42, 0.5)",
  border: "1px solid rgba(148, 163, 184, 0.15)",
}

export function EvidenceLinkTag({ assetName, qcStatus, strength }: Props) {
  const color = strengthColors[strength ?? ""] ?? "#94a3b8"
  return (
    <span style={tagStyle}>
      <span style={{ color: "#e2e8f0" }}>{assetName}</span>
      {qcStatus ? <span style={{ color: "#64748b" }}>· {qcStatus}</span> : null}
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, flexShrink: 0 }} />
    </span>
  )
}
