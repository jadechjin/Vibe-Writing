import type { CSSProperties } from "react"

import type {
  WorkflowSnapshot,
  WorkflowEventRecord,
  Blocker,
} from "../../hooks/useProjectStatus"

// ---- Props ----

export type WorkflowPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  latestBlockers: Blocker[]
  latestEvent: WorkflowEventRecord | null
}>

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
}

const emptyStyle: CSSProperties = {
  textAlign: "center",
  padding: "24px 16px",
  color: "#64748b",
  fontSize: "14px",
}

const cardStyle: CSSProperties = {
  padding: "14px 16px",
  borderRadius: "14px",
  border: "1px solid rgba(148, 163, 184, 0.14)",
  background: "rgba(15, 23, 42, 0.5)",
  display: "flex",
  flexDirection: "column",
  gap: "10px",
}

const sectionLabelStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 700,
  letterSpacing: "0.06em",
  textTransform: "uppercase",
  color: "#94a3b8",
}

const fieldRowStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
  gap: "10px",
}

const fieldLabelStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "#64748b",
}

const fieldValueStyle: CSSProperties = {
  fontSize: "14px",
  color: "#e2e8f0",
}

const eventCardStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "10px 14px",
  borderRadius: "12px",
  border: "1px solid rgba(148, 163, 184, 0.12)",
  background: "rgba(15, 23, 42, 0.4)",
}

const eventTypeBadgeStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  padding: "2px 8px",
  borderRadius: "6px",
  background: "rgba(148, 163, 184, 0.12)",
  color: "#94a3b8",
  whiteSpace: "nowrap",
}

const eventMessageStyle: CSSProperties = {
  fontSize: "13px",
  color: "#cbd5e1",
  flex: 1,
}

const eventTimeStyle: CSSProperties = {
  fontSize: "11px",
  color: "#64748b",
  whiteSpace: "nowrap",
}

const blockerCardStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "12px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
}

const blockerCodeStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#fca5a5",
}

const blockerMsgStyle: CSSProperties = {
  fontSize: "13px",
  color: "#fecaca",
  marginTop: "2px",
}

// ---- Helpers ----

function formatWorkflowStatus(status: string): string {
  switch (status) {
    case "running":
      return "Running"
    case "completed":
      return "Completed"
    case "failed":
      return "Failed"
    case "paused":
      return "Paused"
    case "waiting_user":
      return "Waiting for User"
    default:
      return status
  }
}

// ---- Component ----

export function WorkflowPanel({
  snapshot,
  latestBlockers,
  latestEvent,
}: WorkflowPanelProps) {
  if (!snapshot) {
    return (
      <div style={emptyStyle}>
        Workflow 尚未启动，点击 "Advance Gate" 开始推进。
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      {/* Snapshot summary */}
      <div style={cardStyle}>
        <div style={sectionLabelStyle}>Workflow Snapshot</div>
        <div style={fieldRowStyle}>
          <div>
            <div style={fieldLabelStyle}>State</div>
            <div style={fieldValueStyle}>{snapshot.currentState}</div>
          </div>
          <div>
            <div style={fieldLabelStyle}>Gate</div>
            <div style={fieldValueStyle}>{snapshot.currentGate ?? "N/A"}</div>
          </div>
          <div>
            <div style={fieldLabelStyle}>Status</div>
            <div style={fieldValueStyle}>{formatWorkflowStatus(snapshot.status)}</div>
          </div>
          <div>
            <div style={fieldLabelStyle}>Version</div>
            <div style={fieldValueStyle}>{snapshot.version}</div>
          </div>
        </div>
      </div>

      {/* Latest event */}
      {latestEvent ? (
        <div>
          <div style={sectionLabelStyle}>Latest Event</div>
          <div style={eventCardStyle}>
            <span style={eventTypeBadgeStyle}>{latestEvent.eventType}</span>
            <span style={eventMessageStyle}>{latestEvent.message}</span>
            <span style={eventTimeStyle}>
              {new Date(latestEvent.createdAt).toLocaleTimeString()}
            </span>
          </div>
        </div>
      ) : null}

      {/* Latest blockers */}
      {latestBlockers.length > 0 ? (
        <div>
          <div style={sectionLabelStyle}>Blockers</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {latestBlockers.map((blocker, idx) => (
              <div key={`${blocker.code}-${idx}`} style={blockerCardStyle}>
                <div style={blockerCodeStyle}>{blocker.code}</div>
                <div style={blockerMsgStyle}>{blocker.message}</div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Last error */}
      {snapshot.lastError ? (
        <div style={{ fontSize: "13px", color: "#f87171" }}>
          Last error: {snapshot.lastError}
        </div>
      ) : null}
    </div>
  )
}
