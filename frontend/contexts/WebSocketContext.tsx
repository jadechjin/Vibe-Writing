"use client"

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react"

import {
  createManagedSocket,
  type ConnectionState,
  type TaskEvent,
} from "../lib/websocket"

export const MAX_TASK_EVENTS = 50

type TaskEventSubscriber = (event: TaskEvent) => void

type WebSocketContextValue = Readonly<{
  connectionState: ConnectionState
  events: readonly TaskEvent[]
  subscribe: (subscriber: TaskEventSubscriber) => () => void
}>

const WebSocketContext = createContext<WebSocketContextValue | null>(null)

export function matchesTaskEventScope(
  event: TaskEvent,
  projectId?: string,
  systemId?: string,
): boolean {
  if (projectId && event.projectId !== projectId) {
    return false
  }

  if (systemId && event.systemId !== systemId) {
    return false
  }

  return true
}

export function mergeTaskEventHistory(
  current: readonly TaskEvent[],
  incoming: TaskEvent,
): readonly TaskEvent[] {
  const withoutExisting = current.filter((event) => event.taskId !== incoming.taskId)

  if (withoutExisting.length >= MAX_TASK_EVENTS) {
    return [...withoutExisting.slice(1), incoming]
  }

  return [...withoutExisting, incoming]
}

type WebSocketProviderProps = Readonly<{
  children: ReactNode
  projectId?: string
  systemId?: string
}>

export function WebSocketProvider({
  children,
  projectId,
  systemId,
}: WebSocketProviderProps) {
  const [connectionState, setConnectionState] =
    useState<ConnectionState>("connecting")
  const [events, setEvents] = useState<readonly TaskEvent[]>([])
  const subscribersRef = useRef(new Set<TaskEventSubscriber>())

  const subscribe = useCallback((subscriber: TaskEventSubscriber) => {
    subscribersRef.current.add(subscriber)

    return () => {
      subscribersRef.current.delete(subscriber)
    }
  }, [])

  useEffect(() => {
    setEvents([])

    return createManagedSocket({
      onEvent: (event) => {
        if (!matchesTaskEventScope(event, projectId, systemId)) {
          return
        }

        setEvents((current) => mergeTaskEventHistory(current, event))
        subscribersRef.current.forEach((subscriber) => {
          subscriber(event)
        })
      },
      onStateChange: setConnectionState,
    })
  }, [projectId, systemId])

  const value = useMemo<WebSocketContextValue>(
    () => ({
      connectionState,
      events,
      subscribe,
    }),
    [connectionState, events, subscribe],
  )

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

export function useWebSocketContext(): WebSocketContextValue {
  const context = useContext(WebSocketContext)

  if (!context) {
    throw new Error("useWebSocket must be used within a WebSocketProvider")
  }

  return context
}
