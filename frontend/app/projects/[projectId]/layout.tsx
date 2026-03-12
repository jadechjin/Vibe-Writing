"use client"

import { type CSSProperties, type ReactNode, useCallback, useEffect, useRef } from "react"
import { useParams } from "next/navigation"

import { WebSocketProvider, useWebSocketContext } from "../../../contexts/WebSocketContext"
import { ProjectBreadcrumb } from "../../../components/layout/ProjectBreadcrumb"
import { useProjectInvalidation } from "../../../hooks/useProjects"
import { ToastProvider } from "../../../hooks/useToast"
import type { TaskEvent } from "../../../lib/websocket"

const containerStyle: CSSProperties = {
  minHeight: "100vh",
  background:
    "radial-gradient(circle at top, rgba(30, 64, 175, 0.18), transparent 34%), linear-gradient(180deg, #020617 0%, #0f172a 56%, #111827 100%)",
  color: "#e2e8f0",
  padding: "32px 24px",
  maxWidth: "1440px",
  margin: "0 auto",
}

const INVALIDATION_EVENT_TYPES = new Set([
  "gate.passed",
  "workflow.state_changed",
  "task.succeeded",
])

const DEBOUNCE_MS = 500

function ProjectEventHandler({ projectId }: Readonly<{ projectId: string }>) {
  const { subscribe } = useWebSocketContext()
  const invalidate = useProjectInvalidation(projectId)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleEvent = useCallback(
    (event: TaskEvent) => {
      if (!INVALIDATION_EVENT_TYPES.has(event.type)) return

      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        invalidate()
        timerRef.current = null
      }, DEBOUNCE_MS)
    },
    [invalidate],
  )

  useEffect(() => {
    const unsub = subscribe(handleEvent)
    return () => {
      unsub()
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [subscribe, handleEvent])

  return null
}

export default function ProjectLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  const params = useParams<{ projectId: string }>()
  const projectId = params.projectId

  return (
    <WebSocketProvider projectId={projectId}>
      <ToastProvider>
        <ProjectEventHandler projectId={projectId} />
        <div style={containerStyle}>
          <ProjectBreadcrumb projectId={projectId} />
          {children}
        </div>
      </ToastProvider>
    </WebSocketProvider>
  )
}
