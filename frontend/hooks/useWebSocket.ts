"use client"

import { useEffect, useMemo, useRef } from "react"

import {
  useWebSocketContext,
  matchesTaskEventScope,
} from "../contexts/WebSocketContext"
import type { ConnectionState, TaskEvent } from "../lib/websocket"

export type UseWebSocketOptions = {
  projectId?: string
  systemId?: string
  onInvalidate?: (event: TaskEvent) => void
}

export type UseWebSocketReturn = {
  connectionState: ConnectionState
  events: readonly TaskEvent[]
}

export function useWebSocket(
  options: UseWebSocketOptions = {},
): UseWebSocketReturn {
  const { projectId, systemId, onInvalidate } = options
  const { connectionState, events: providerEvents, subscribe } = useWebSocketContext()

  const onInvalidateRef = useRef(onInvalidate)
  onInvalidateRef.current = onInvalidate

  const projectIdRef = useRef(projectId)
  projectIdRef.current = projectId

  const systemIdRef = useRef(systemId)
  systemIdRef.current = systemId

  useEffect(() => {
    return subscribe((event) => {
      if (!matchesTaskEventScope(event, projectIdRef.current, systemIdRef.current)) {
        return
      }

      onInvalidateRef.current?.(event)
    })
  }, [subscribe])

  const events = useMemo(
    () =>
      providerEvents.filter((event) =>
        matchesTaskEventScope(event, projectId, systemId),
      ),
    [projectId, providerEvents, systemId],
  )

  return { connectionState, events }
}
