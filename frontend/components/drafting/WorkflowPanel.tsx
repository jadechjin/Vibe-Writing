import type { CSSProperties } from "react"

import type {
  WorkflowSnapshot,
  WorkflowEventRecord,
  Blocker,
} from "../../hooks/useProjectStatus"
import { resolveBlockerDisplay } from "../../lib/blockerMessages"

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

const blockerSectionStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  padding: "14px 16px",
  borderRadius: "14px",
  border: "1px solid rgba(248, 113, 113, 0.25)",
  background: "rgba(127, 29, 29, 0.1)",
}

const blockerTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 700,
  color: "#fca5a5",
}

const blockerCardStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(248, 113, 113, 0.15)",
  background: "rgba(15, 23, 42, 0.4)",
  display: "flex",
  flexDirection: "column",
  gap: "4px",
}

const warningCardStyle: CSSProperties = {
  ...blockerCardStyle,
  border: "1px solid rgba(251, 191, 36, 0.15)",
}

const blockerLabelStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#fecaca",
}

const warningLabelStyle: CSSProperties = {
  ...blockerLabelStyle,
  color: "#fde68a",
}

const blockerDetailStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
  lineHeight: 1.5,
}

// ---- Helpers ----

function formatWorkflowStatus(status: string): string {
  switch (status) {
    case "running":
      return "运行中"
    case "completed":
      return "已完成"
    case "failed":
      return "失败"
    case "paused":
      return "已暂停"
    case "waiting_user":
      return "等待用户"
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
        Workflow 尚未启动，点击"推进 Gate"开始推进。
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      {/* Snapshot summary */}
      <div style={cardStyle}>
        <div style={sectionLabelStyle}>工作流快照</div>
        <div style={fieldRowStyle}>
          <div>
            <div style={fieldLabelStyle}>状态</div>
            <div style={fieldValueStyle}>{snapshot.currentState}</div>
          </div>
          <div>
            <div style={fieldLabelStyle}>门禁</div>
            <div style={fieldValueStyle}>{snapshot.currentGate ?? "N/A"}</div>
          </div>
          <div>
            <div style={fieldLabelStyle}>运行状态</div>
            <div style={fieldValueStyle}>{formatWorkflowStatus(snapshot.status)}</div>
          </div>
          <div>
            <div style={fieldLabelStyle}>版本</div>
            <div style={fieldValueStyle}>{snapshot.version}</div>
          </div>
        </div>
      </div>

      {/* Latest event */}
      {latestEvent ? (
        <div>
          <div style={sectionLabelStyle}>最新事件</div>
          <div style={eventCardStyle}>
            <span style={eventTypeBadgeStyle}>{latestEvent.eventType}</span>
            <span style={eventMessageStyle}>{latestEvent.message}</span>
            <span style={eventTimeStyle}>
              {new Date(latestEvent.createdAt).toLocaleTimeString()}
            </span>
          </div>
        </div>
      ) : null}

      {/* Blockers & Warnings */}
      {latestBlockers.length > 0 ? (() => {
        const NON_BLOCKING_CODES = new Set(["snapshot_stale", "section_missing_claims"])
        const blockers = latestBlockers.filter((b) => !NON_BLOCKING_CODES.has(b.code))
        const warnings = latestBlockers.filter((b) => NON_BLOCKING_CODES.has(b.code))
        return (
          <>
            {blockers.length > 0 ? (
              <div style={blockerSectionStyle}>
                <div style={blockerTitleStyle}>阻塞项（{blockers.length}）</div>
                {blockers.map((blocker, idx) => {
                  const display = resolveBlockerDisplay(blocker)
                  return (
                    <div key={`${blocker.code}-${idx}`} style={blockerCardStyle}>
                      <div style={blockerLabelStyle}>{display.label}</div>
                      <div style={blockerDetailStyle}>{display.detail}</div>
                    </div>
                  )
                })}
              </div>
            ) : null}
            {warnings.length > 0 ? (
              <div style={{ ...blockerSectionStyle, border: "1px solid rgba(251, 191, 36, 0.2)", background: "rgba(120, 53, 15, 0.08)" }}>
                <div style={{ ...blockerTitleStyle, color: "#fbbf24" }}>提示（{warnings.length}）</div>
                {warnings.map((blocker, idx) => {
                  const display = resolveBlockerDisplay(blocker)
                  return (
                    <div key={`${blocker.code}-${idx}`} style={warningCardStyle}>
                      <div style={warningLabelStyle}>{display.label}</div>
                      <div style={blockerDetailStyle}>{display.detail}</div>
                    </div>
                  )
                })}
              </div>
            ) : null}
          </>
        )
      })() : null}

      {/* Last error */}
      {snapshot.lastError ? (
        <div style={{ fontSize: "13px", color: "#f87171" }}>
          最近错误：{snapshot.lastError}
        </div>
      ) : null}
    </div>
  )
}
