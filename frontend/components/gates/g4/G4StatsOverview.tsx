"use client"

import type { CSSProperties } from "react"

type Props = {
  claimCount: number
  approvedCount: number
  pendingCount: number
  bindingCount: number
  sectionCount: number
  coveredSectionCount: number
  coverageRate: number
}

const gridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
  gap: "10px",
}

const cardStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.12)",
  background: "rgba(15, 23, 42, 0.35)",
}

const valueStyle: CSSProperties = { fontSize: "18px", fontWeight: 700, color: "#f8fafc" }
const labelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
  marginTop: "4px",
}

export function G4StatsOverview({ claimCount, approvedCount, pendingCount, bindingCount, sectionCount, coveredSectionCount, coverageRate }: Props) {
  const items = [
    { value: claimCount, label: "Claims" },
    { value: approvedCount, label: "已批准" },
    { value: pendingCount, label: "待处理" },
    { value: `${coveredSectionCount}/${sectionCount}`, label: "章节覆盖" },
    { value: bindingCount, label: "绑定数" },
    { value: `${Math.round(coverageRate * 100)}%`, label: "覆盖率" },
  ]

  return (
    <div style={gridStyle}>
      {items.map(({ value, label }) => (
        <div key={label} style={cardStyle}>
          <div style={valueStyle}>{value}</div>
          <div style={labelStyle}>{label}</div>
        </div>
      ))}
    </div>
  )
}
