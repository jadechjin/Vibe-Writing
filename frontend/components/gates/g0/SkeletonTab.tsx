"use client"

import { type CSSProperties } from "react"

import { useSkeletons, useGenerateSkeleton } from "../../../hooks/useSkeletons"

// ---- Props ----

export type SkeletonTabProps = Readonly<{
  systemId: string
  isReadOnly: boolean
  onOpenOverlay: (mode?: "list" | "generating") => void
}>

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex", flexDirection: "column", gap: "14px",
}

const headerStyle: CSSProperties = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
}

const titleStyle: CSSProperties = { fontSize: "14px", fontWeight: 700, color: "#f8fafc" }

const btnStyle: CSSProperties = {
  padding: "6px 14px", borderRadius: "10px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "12px", fontWeight: 600, color: "#fb923c", cursor: "pointer",
}

const btnDisabledStyle: CSSProperties = { ...btnStyle, opacity: 0.4, cursor: "not-allowed" }

const summaryCardStyle: CSSProperties = {
  padding: "16px", borderRadius: "12px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.5)",
  display: "flex", flexDirection: "column", gap: "10px",
  cursor: "pointer",
}

const statRow: CSSProperties = {
  display: "flex", gap: "16px", alignItems: "center",
}

const statLabel: CSSProperties = { fontSize: "12px", color: "#64748b" }
const statValue: CSSProperties = { fontSize: "13px", fontWeight: 600, color: "#e2e8f0" }

const openBtnStyle: CSSProperties = {
  ...btnStyle,
  border: "1px solid rgba(96, 165, 250, 0.5)",
  background: "rgba(30, 64, 175, 0.15)",
  color: "#60a5fa",
  textAlign: "center",
}

const emptyStyle: CSSProperties = {
  fontSize: "13px", color: "#64748b", textAlign: "center", padding: "24px 0",
}

// ---- Component ----

export function SkeletonTab({ systemId, isReadOnly, onOpenOverlay }: SkeletonTabProps) {
  const { data: skeletons, isLoading } = useSkeletons(systemId)
  const generateMut = useGenerateSkeleton(systemId)

  const canGenerate = !isReadOnly && !generateMut.isPending
  const latest = skeletons?.[0]
  const confirmedCount = skeletons?.filter((s) => s.status === "confirmed").length ?? 0
  const draftCount = skeletons?.filter((s) => s.status === "draft").length ?? 0

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={titleStyle}>结构骨架 ({skeletons?.length ?? 0})</div>
        {!isReadOnly ? (
          <button type="button"
            onClick={() => onOpenOverlay("generating")}
            disabled={!canGenerate}
            style={canGenerate ? btnStyle : btnDisabledStyle}>
            AI 生成
          </button>
        ) : null}
      </div>

      {isLoading ? (
        <div style={emptyStyle}>加载中...</div>
      ) : !skeletons || skeletons.length === 0 ? (
        <div style={emptyStyle}>暂无结构骨架，点击「AI 生成」创建</div>
      ) : (
        <div style={summaryCardStyle} onClick={() => onOpenOverlay()}
          role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenOverlay() }}>
          <div style={statRow}>
            <div><span style={statLabel}>最新版本 </span><span style={statValue}>v{latest?.version}</span></div>
            <div><span style={statLabel}>状态 </span><span style={statValue}>{latest?.status}</span></div>
          </div>
          <div style={statRow}>
            <div><span style={statLabel}>已确认 </span><span style={statValue}>{confirmedCount}</span></div>
            <div><span style={statLabel}>草稿 </span><span style={statValue}>{draftCount}</span></div>
          </div>
          {latest?.changeSummary ? (
            <div style={{ fontSize: "12px", color: "#94a3b8" }}>{latest.changeSummary}</div>
          ) : null}
          <button type="button" style={openBtnStyle} onClick={(e) => { e.stopPropagation(); onOpenOverlay() }}>
            打开骨架管理
          </button>
        </div>
      )}
    </div>
  )
}
