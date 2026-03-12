"use client"

import type { CSSProperties } from "react"

import type { ConnectionState, TaskEvent } from "../../lib/websocket"
import type { GateKey } from "../../lib/gateMapping"
import { useWebSocket, type UseWebSocketOptions } from "../../hooks/useWebSocket"
import { TaskItem } from "./TaskItem"

type StatusTrayProps = Readonly<{
  projectId?: string
  systemId?: string
  onInvalidate?: (event: TaskEvent) => void
  onNavigate?: (gateKey: GateKey) => void
}>

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: "8px",
}

const titleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 700,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "#94a3b8",
}

const CONNECTION_INDICATOR: Record<ConnectionState, { label: string; color: string }> = {
  connecting: { label: "连接中...", color: "#fbbf24" },
  open: { label: "已连接", color: "#4ade80" },
  closed: { label: "已断开", color: "#f87171" },
}

const dotStyle: CSSProperties = {
  display: "inline-block",
  width: "7px",
  height: "7px",
  borderRadius: "50%",
  marginRight: "6px",
}

const connectionStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  fontSize: "12px",
  color: "#94a3b8",
}

const emptyStyle: CSSProperties = {
  fontSize: "13px",
  color: "#64748b",
  padding: "4px 0",
}

const listStyle: CSSProperties = {
  maxHeight: "180px",
  overflowY: "auto",
}

export function StatusTray({ projectId, systemId, onInvalidate, onNavigate }: StatusTrayProps) {
  const options: UseWebSocketOptions = { projectId, systemId, onInvalidate }
  const { connectionState, events } = useWebSocket(options)
  const indicator = CONNECTION_INDICATOR[connectionState]

  return (
    <section>
      <div style={headerStyle}>
        <span style={titleStyle}>任务状态</span>
        <span style={connectionStyle}>
          <span style={{ ...dotStyle, background: indicator.color }} />
          {indicator.label}
        </span>
      </div>
      {events.length === 0 ? (
        <div style={emptyStyle}>暂无活跃任务</div>
      ) : (
        <div style={listStyle}>
          {events.map((event) => (
            <TaskItem key={event.taskId} event={event} onNavigate={onNavigate} />
          ))}
        </div>
      )}
    </section>
  )
}
