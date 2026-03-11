const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/tasks"

const MIN_RECONNECT_MS = 1_000
const MAX_RECONNECT_MS = 30_000
const BACKOFF_FACTOR = 2

export type TaskStatus =
  | "queued"
  | "running"
  | "waiting_user"
  | "succeeded"
  | "failed"
  | "cancelled"

export type TaskEvent = {
  type: string
  taskId: string
  workflowId?: string
  projectId: string
  systemId?: string
  status: TaskStatus
  progress?: number
  message: string
  timestamp: string
  payload?: Record<string, unknown>
}

const VALID_STATUSES: ReadonlySet<string> = new Set<TaskStatus>([
  "queued",
  "running",
  "waiting_user",
  "succeeded",
  "failed",
  "cancelled",
])

export function parseTaskEvent(raw: unknown): TaskEvent | null {
  if (!raw || typeof raw !== "object") {
    return null
  }

  const candidate = raw as Record<string, unknown>

  if (
    typeof candidate.type !== "string" ||
    typeof candidate.taskId !== "string" ||
    typeof candidate.projectId !== "string" ||
    typeof candidate.status !== "string" ||
    typeof candidate.message !== "string" ||
    typeof candidate.timestamp !== "string" ||
    !VALID_STATUSES.has(candidate.status)
  ) {
    return null
  }

  return {
    type: candidate.type,
    taskId: candidate.taskId,
    projectId: candidate.projectId,
    status: candidate.status as TaskStatus,
    message: candidate.message,
    timestamp: candidate.timestamp,
    workflowId:
      typeof candidate.workflowId === "string" ? candidate.workflowId : undefined,
    systemId:
      typeof candidate.systemId === "string" ? candidate.systemId : undefined,
    progress:
      typeof candidate.progress === "number" ? candidate.progress : undefined,
    payload:
      candidate.payload && typeof candidate.payload === "object"
        ? (candidate.payload as Record<string, unknown>)
        : undefined,
  }
}

export type ConnectionState = "connecting" | "open" | "closed"

export type SocketCallbacks = {
  onEvent: (event: TaskEvent) => void
  onStateChange: (state: ConnectionState) => void
}

export function createManagedSocket(callbacks: SocketCallbacks): () => void {
  let active = true
  let socket: WebSocket | undefined
  let reconnectTimer: ReturnType<typeof setTimeout> | undefined
  let attempt = 0

  function nextDelay(): number {
    const delay = Math.min(
      MIN_RECONNECT_MS * Math.pow(BACKOFF_FACTOR, attempt),
      MAX_RECONNECT_MS,
    )
    attempt += 1
    return delay
  }

  function connect() {
    if (!active) {
      return
    }

    callbacks.onStateChange("connecting")
    socket = new WebSocket(WS_URL)

    socket.onopen = () => {
      if (!active) {
        return
      }
      attempt = 0
      callbacks.onStateChange("open")
    }

    socket.onmessage = (event) => {
      if (!active) {
        return
      }
      try {
        const parsed = parseTaskEvent(JSON.parse(event.data) as unknown)
        if (parsed) {
          callbacks.onEvent(parsed)
        }
      } catch {
        // malformed frame, skip
      }
    }

    socket.onerror = () => {
      // onclose will fire after onerror, reconnect handled there
    }

    socket.onclose = () => {
      if (!active) {
        return
      }
      callbacks.onStateChange("closed")
      reconnectTimer = setTimeout(connect, nextDelay())
    }
  }

  connect()

  return () => {
    active = false
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    if (socket) {
      socket.close()
    }
  }
}
