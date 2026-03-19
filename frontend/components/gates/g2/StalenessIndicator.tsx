"use client"

import type { CSSProperties } from "react"

type Props = {
  outlineFingerprint?: string
  currentFingerprint?: string
}

const barStyle: CSSProperties = {
  padding: "8px 14px",
  borderRadius: "8px",
  background: "rgba(251, 191, 36, 0.1)",
  border: "1px solid rgba(251, 191, 36, 0.25)",
  fontSize: "12px",
  color: "#fde68a",
  display: "flex",
  alignItems: "center",
  gap: "6px",
}

export function StalenessIndicator({ outlineFingerprint, currentFingerprint }: Props) {
  if (!outlineFingerprint || !currentFingerprint) return null
  if (outlineFingerprint === currentFingerprint) return null

  return (
    <div style={barStyle}>
      <span style={{ fontSize: "14px" }}>⚠</span>
      提纲基于旧版本数据（{outlineFingerprint.slice(0, 8)}...），当前快照为 {currentFingerprint.slice(0, 8)}...，建议重新生成。
    </div>
  )
}
