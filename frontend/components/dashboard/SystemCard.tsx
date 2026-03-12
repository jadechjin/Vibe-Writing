import { type CSSProperties, type MouseEvent, useCallback, useState } from "react"

import { GATE_ORDER, countCompletedGatesFromStatus } from "../../lib/gates"
import type { ProjectSystemSummary } from "../../hooks/useProjects"

type SystemCardProps = Readonly<{
  system: ProjectSystemSummary
  projectId: string
  onDelete?: (systemId: string) => void
  deleteError?: string | null
  isDeleting?: boolean
}>

const STATUS_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  complete: {
    bg: "rgba(20, 83, 45, 0.25)",
    border: "rgba(34, 197, 94, 0.5)",
    text: "#4ade80",
  },
  active: {
    bg: "rgba(154, 52, 18, 0.18)",
    border: "rgba(249, 115, 22, 0.45)",
    text: "#fb923c",
  },
  draft: {
    bg: "rgba(51, 65, 85, 0.3)",
    border: "rgba(148, 163, 184, 0.25)",
    text: "#94a3b8",
  },
}

function resolveStatusColor(status: string) {
  if (status === "Chapter_Approved") return STATUS_COLORS.complete
  if (status === "Draft") return STATUS_COLORS.draft
  return STATUS_COLORS.active
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 1) return "刚刚"
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  return `${days}天前`
}

const cardStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
  padding: "16px 18px",
  borderRadius: "14px",
  border: "1px solid rgba(148, 163, 184, 0.16)",
  background: "rgba(15, 23, 42, 0.6)",
  cursor: "pointer",
  textDecoration: "none",
  color: "inherit",
  transition: "border-color 0.15s",
}

const cardHeaderStyle: CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "space-between",
  gap: "12px",
}

const systemNoStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#93c5fd",
  letterSpacing: "0.04em",
}

const systemTitleStyle: CSSProperties = {
  fontSize: "15px",
  fontWeight: 600,
  color: "#f8fafc",
  marginTop: "2px",
}

const headerRightStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  flexShrink: 0,
}

const badgeBaseStyle: CSSProperties = {
  padding: "4px 10px",
  borderRadius: "8px",
  fontSize: "11px",
  fontWeight: 600,
  whiteSpace: "nowrap",
}

const deleteBtnStyle: CSSProperties = {
  padding: "4px 8px",
  borderRadius: "6px",
  border: "1px solid rgba(248, 113, 113, 0.3)",
  background: "transparent",
  color: "#f87171",
  fontSize: "12px",
  cursor: "pointer",
  lineHeight: 1,
}

const progressTrackStyle: CSSProperties = {
  height: "6px",
  borderRadius: "3px",
  background: "rgba(51, 65, 85, 0.5)",
  overflow: "hidden",
}

const progressFillBaseStyle: CSSProperties = {
  height: "100%",
  borderRadius: "3px",
  transition: "width 0.3s ease",
}

const footerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  fontSize: "12px",
  color: "#64748b",
}

const confirmBarStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "10px",
  padding: "10px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(248, 113, 113, 0.3)",
  background: "rgba(127, 29, 29, 0.15)",
  fontSize: "13px",
  color: "#fca5a5",
}

const confirmBtnStyle: CSSProperties = {
  padding: "4px 12px",
  borderRadius: "6px",
  border: "1px solid rgba(248, 113, 113, 0.5)",
  background: "rgba(127, 29, 29, 0.4)",
  color: "#fca5a5",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
}

const cancelConfirmBtnStyle: CSSProperties = {
  padding: "4px 12px",
  borderRadius: "6px",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  background: "transparent",
  color: "#94a3b8",
  fontSize: "12px",
  cursor: "pointer",
}

const errorStyle: CSSProperties = {
  fontSize: "12px",
  color: "#f87171",
  padding: "6px 0 0",
}

export function SystemCard({
  system,
  projectId,
  onDelete,
  deleteError,
  isDeleting,
}: SystemCardProps) {
  const [confirming, setConfirming] = useState(false)

  const completed = countCompletedGatesFromStatus(system.status)
  const total = GATE_ORDER.length
  const pct = Math.round((completed / total) * 100)
  const color = resolveStatusColor(system.status)
  const displayStatus = system.status.replace(/_/g, " ")

  const handleNavigate = useCallback(() => {
    if (!confirming) {
      window.location.href = `/projects/${projectId}/systems/${system.id}`
    }
  }, [confirming, projectId, system.id])

  const handleDeleteClick = useCallback((e: MouseEvent) => {
    e.stopPropagation()
    setConfirming(true)
  }, [])

  const handleConfirmDelete = useCallback(
    (e: MouseEvent) => {
      e.stopPropagation()
      onDelete?.(system.id)
    },
    [onDelete, system.id],
  )

  const handleCancelDelete = useCallback((e: MouseEvent) => {
    e.stopPropagation()
    setConfirming(false)
  }, [])

  return (
    <div
      role="link"
      tabIndex={0}
      style={cardStyle}
      onClick={handleNavigate}
      onKeyDown={(e) => {
        if (e.key === "Enter") handleNavigate()
      }}
    >
      <div style={cardHeaderStyle}>
        <div>
          <div style={systemNoStyle}>#{system.systemNo}</div>
          <div style={systemTitleStyle}>{system.title}</div>
        </div>
        <div style={headerRightStyle}>
          <span
            style={{
              ...badgeBaseStyle,
              background: color.bg,
              border: `1px solid ${color.border}`,
              color: color.text,
            }}
          >
            {displayStatus}
          </span>
          {onDelete ? (
            <button
              type="button"
              style={deleteBtnStyle}
              onClick={handleDeleteClick}
              disabled={isDeleting}
              aria-label={`删除体系 ${system.title}`}
            >
              {isDeleting ? "..." : "\u2715"}
            </button>
          ) : null}
        </div>
      </div>

      {confirming ? (
        <div style={confirmBarStyle} onClick={(e) => e.stopPropagation()}>
          <span>确定删除该体系？</span>
          <div style={{ display: "flex", gap: "6px" }}>
            <button type="button" style={cancelConfirmBtnStyle} onClick={handleCancelDelete}>
              取消
            </button>
            <button
              type="button"
              style={confirmBtnStyle}
              onClick={handleConfirmDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "删除中..." : "删除"}
            </button>
          </div>
        </div>
      ) : null}

      <div style={progressTrackStyle}>
        <div
          style={{
            ...progressFillBaseStyle,
            width: `${pct}%`,
            background: pct === 100
              ? "linear-gradient(90deg, #16a34a, #4ade80)"
              : "linear-gradient(90deg, #3b82f6, #60a5fa)",
          }}
        />
      </div>

      <div style={footerStyle}>
        <span>
          {completed}/{total} gates
          {pct === 100 ? " \u2014 已完成" : ""}
        </span>
        <span>{formatRelativeTime(system.updatedAt)}</span>
      </div>

      {deleteError ? <div style={errorStyle}>{deleteError}</div> : null}
    </div>
  )
}
