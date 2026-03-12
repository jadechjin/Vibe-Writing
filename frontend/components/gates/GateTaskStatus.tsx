"use client"

import { useEffect, useState, type CSSProperties } from "react"

import { useWebSocketContext } from "../../contexts/WebSocketContext"
import { getGateKeyFromTaskEvent, type GateKey } from "../../lib/gateMapping"
import type { TaskEvent } from "../../lib/websocket"

type GateTaskStatusProps = Readonly<{
  systemId: string
  gateKey: GateKey
}>

const containerStyle: CSSProperties = {
  padding: "12px 16px",
  background: "rgba(96, 165, 250, 0.08)",
  border: "1px solid rgba(96, 165, 250, 0.24)",
  borderRadius: "8px",
  marginBottom: "16px",
}

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  marginBottom: "8px",
}

const titleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "#60a5fa",
}

const dotStyle: CSSProperties = {
  display: "inline-block",
  width: "6px",
  height: "6px",
  borderRadius: "50%",
  background: "#60a5fa",
  animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
}

const messageStyle: CSSProperties = {
  fontSize: "13px",
  color: "#cbd5e1",
  lineHeight: 1.4,
}

const progressContainerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  marginTop: "8px",
}

const progressBarOuter: CSSProperties = {
  flex: 1,
  height: "6px",
  borderRadius: "3px",
  background: "rgba(148, 163, 184, 0.15)",
  overflow: "hidden",
}

const percentageStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  color: "#94a3b8",
  minWidth: "32px",
  textAlign: "right",
}

function ProgressBar({ value, indeterminate }: Readonly<{ value: number; indeterminate?: boolean }>) {
  if (indeterminate) {
    return (
      <div style={progressBarOuter}>
        <div
          style={{
            width: "40%",
            height: "100%",
            borderRadius: "3px",
            background: "#60a5fa",
            animation: "indeterminate-slide 1.4s ease-in-out infinite",
          }}
        />
      </div>
    )
  }

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

function isActiveTask(event: TaskEvent): boolean {
  return event.status === "running" || event.status === "waiting_user"
}

function isSucceededTask(event: TaskEvent): boolean {
  return event.status === "succeeded"
}

export function GateTaskStatus({ systemId, gateKey }: GateTaskStatusProps) {
  const { events } = useWebSocketContext()
  const [showSucceeded, setShowSucceeded] = useState<string | null>(null)

  const activeTask = events.find(
    (event) =>
      event.systemId === systemId &&
      getGateKeyFromTaskEvent(event) === gateKey &&
      isActiveTask(event),
  )

  const succeededTask = events.find(
    (event) =>
      event.systemId === systemId &&
      getGateKeyFromTaskEvent(event) === gateKey &&
      isSucceededTask(event),
  )

  const succeededTaskId = succeededTask?.taskId ?? null

  useEffect(() => {
    if (succeededTaskId) {
      setShowSucceeded(succeededTaskId)
      const timer = setTimeout(() => setShowSucceeded(null), 1500)
      return () => clearTimeout(timer)
    }
  }, [succeededTaskId])

  if (!activeTask && !showSucceeded) {
    return null
  }

  const isRunning = !!activeTask && activeTask.status === "running"
  const hasNumericProgress = typeof activeTask?.progress === "number"
  const showIndeterminate = isRunning && !hasNumericProgress

  return (
    <>
      <style>{`
        @keyframes indeterminate-slide {
          0% { transform: translateX(-200%); }
          100% { transform: translateX(350%); }
        }
      `}</style>
      <div style={containerStyle}>
        <div style={headerStyle}>
          <span style={dotStyle} />
          <span style={titleStyle}>{showSucceeded ? "Completed" : "Active Task"}</span>
        </div>
        <div style={messageStyle}>{activeTask?.message ?? "Task completed."}</div>
        <div style={progressContainerStyle}>
          {showSucceeded ? (
            <ProgressBar value={100} />
          ) : showIndeterminate ? (
            <ProgressBar value={0} indeterminate />
          ) : hasNumericProgress ? (
            <>
              <ProgressBar value={activeTask!.progress as number} />
              <span style={percentageStyle}>{Math.round(activeTask!.progress as number)}%</span>
            </>
          ) : null}
        </div>
      </div>
    </>
  )
}
