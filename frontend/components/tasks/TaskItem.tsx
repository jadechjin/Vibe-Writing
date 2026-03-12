"use client"

import type { CSSProperties, ReactNode } from "react"

import {
  getGateKeyFromTaskEvent,
  getTaskTypeFromTaskId,
  type GateKey,
} from "../../lib/gateMapping"
import type { TaskEvent, TaskStatus } from "../../lib/websocket"

type TaskItemProps = Readonly<{
  event: TaskEvent
  onNavigate?: (gateKey: GateKey) => void
}>

const STATUS_META: Record<TaskStatus, { label: string; color: string }> = {
  queued: { label: "排队中", color: "#94a3b8" },
  running: { label: "运行中", color: "#60a5fa" },
  waiting_user: { label: "等待中", color: "#fbbf24" },
  succeeded: { label: "已完成", color: "#4ade80" },
  failed: { label: "失败", color: "#f87171" },
  cancelled: { label: "已取消", color: "#a1a1aa" },
}

const itemStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "auto auto minmax(0, 1fr) auto auto",
  alignItems: "center",
  gap: "10px",
  width: "100%",
  padding: "8px 12px",
  borderBottom: "1px solid rgba(148, 163, 184, 0.08)",
  borderRadius: "10px",
  background: "transparent",
  textAlign: "left",
  transition: "background 0.2s ease",
}

const interactiveItemStyle: CSSProperties = {
  ...itemStyle,
  border: "none",
  cursor: "pointer",
}

const badgeBaseStyle: CSSProperties = {
  display: "inline-block",
  fontSize: "10px",
  fontWeight: 700,
  letterSpacing: "0.04em",
  padding: "2px 6px",
  borderRadius: "6px",
  textTransform: "uppercase",
  lineHeight: "16px",
  whiteSpace: "nowrap",
}

const messageStyle: CSSProperties = {
  fontSize: "13px",
  color: "#cbd5e1",
  lineHeight: 1.4,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

const taskTypeStyle: CSSProperties = {
  ...badgeBaseStyle,
  color: "#94a3b8",
  background: "rgba(148, 163, 184, 0.12)",
  border: "1px solid rgba(148, 163, 184, 0.24)",
}

const progressContainerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
}

const progressBarOuter: CSSProperties = {
  width: "48px",
  height: "6px",
  borderRadius: "3px",
  background: "rgba(148, 163, 184, 0.15)",
  overflow: "hidden",
}

const percentageStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "#94a3b8",
  minWidth: "28px",
  textAlign: "right",
}

function ProgressBar({ value }: Readonly<{ value: number }>) {
  const innerStyle: CSSProperties = {
    width: `${Math.min(100, Math.max(0, value))}%`,
    height: "100%",
    borderRadius: "3px",
    background: "#60a5fa",
    transition: "width 0.3s ease",
  }

  return (
    <div style={progressBarOuter}>
      <div style={innerStyle} />
    </div>
  )
}

function formatTaskTypeLabel(taskType: string | null): string {
  if (!taskType) {
    return "任务"
  }

  return taskType
    .replace(/_/g, " ")
    .replace(/\b\w/g, (segment) => segment.toUpperCase())
}

function renderTaskRowContent(
  event: TaskEvent,
  statusLabel: string,
  statusColor: string,
  mappedGate: GateKey | null,
): ReactNode {
  const badgeStyle: CSSProperties = {
    ...badgeBaseStyle,
    color: statusColor,
    background: `${statusColor}1a`,
    border: `1px solid ${statusColor}33`,
  }

  const taskTypeLabel = formatTaskTypeLabel(getTaskTypeFromTaskId(event.taskId))

  return (
    <>
      <span style={badgeStyle}>{statusLabel}</span>
      <span style={taskTypeStyle}>{taskTypeLabel}</span>
      <span style={messageStyle} title={event.message}>
        {event.message}
      </span>
      {typeof event.progress === "number" ? (
        <div style={progressContainerStyle}>
          <ProgressBar value={event.progress} />
          <span style={percentageStyle}>{Math.round(event.progress)}%</span>
        </div>
      ) : (
        <span />
      )}
      <span style={percentageStyle}>{mappedGate ?? ""}</span>
    </>
  )
}

export function TaskItem({ event, onNavigate }: TaskItemProps) {
  const meta = STATUS_META[event.status]
  const mappedGate = getGateKeyFromTaskEvent(event)
  const isClickable = Boolean(mappedGate && onNavigate)
  const content = renderTaskRowContent(event, meta.label, meta.color, mappedGate)

  if (isClickable && mappedGate) {
    return (
      <button
        type="button"
        style={interactiveItemStyle}
        onClick={() => onNavigate?.(mappedGate)}
        title={`打开 ${mappedGate}`}
        aria-label={`打开 ${mappedGate} 工作台，任务 ${event.taskId}`}
      >
        {content}
      </button>
    )
  }

  return <div style={itemStyle}>{content}</div>
}
