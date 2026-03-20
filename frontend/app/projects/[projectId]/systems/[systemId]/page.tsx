"use client"

import { type CSSProperties, useCallback, useEffect, useMemo, useState } from "react"
import { useParams } from "next/navigation"

import { MainShell } from "../../../../../components/layout/MainShell"
import { EvidenceHub } from "../../../../../components/evidence/EvidenceHub"
import { GatePanel } from "../../../../../components/gates/GatePanel"
import { StatusTray } from "../../../../../components/tasks/StatusTray"
import { WebSocketProvider } from "../../../../../contexts/WebSocketContext"
import type { GateKey } from "../../../../../lib/gateMapping"
import { resolveBlockerDisplay } from "../../../../../lib/blockerMessages"
import { useProjectStatus, useWorkflowInvalidation } from "../../../../../hooks/useProjectStatus"
import {
  useSystemAdvance,
  type AdvanceResponse,
} from "../../../../../hooks/useSystemAdvance"
import { useSystemDetail } from "../../../../../hooks/useSystem"
import type { TaskEvent } from "../../../../../lib/websocket"

// ---- Styles ----

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "flex-start",
  justifyContent: "space-between",
  gap: "16px",
  marginBottom: "4px",
}

const titleStyle: CSSProperties = {
  fontSize: "20px",
  fontWeight: 700,
  color: "#f8fafc",
}

const subtitleStyle: CSSProperties = {
  fontSize: "13px",
  color: "#94a3b8",
  marginTop: "4px",
}

const advanceBtnStyle: CSSProperties = {
  padding: "10px 24px",
  borderRadius: "12px",
  border: "1px solid rgba(34, 197, 94, 0.6)",
  background: "rgba(20, 83, 45, 0.3)",
  color: "#4ade80",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
}

const advanceBtnDisabledStyle: CSSProperties = {
  ...advanceBtnStyle,
  opacity: 0.5,
  cursor: "not-allowed",
}

const emptyStyle: CSSProperties = {
  textAlign: "center",
  padding: "36px 24px",
  color: "#64748b",
  fontSize: "14px",
}

const outcomeBlockedStyle: CSSProperties = {
  padding: "16px 18px",
  borderRadius: "14px",
  border: "1px solid rgba(248, 113, 113, 0.3)",
  background: "rgba(127, 29, 29, 0.15)",
  marginBottom: "4px",
}

const outcomeAcceptedStyle: CSSProperties = {
  padding: "16px 18px",
  borderRadius: "14px",
  border: "1px solid rgba(74, 222, 128, 0.3)",
  background: "rgba(20, 83, 45, 0.15)",
  marginBottom: "4px",
}

const blockerItemStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  marginTop: "8px",
}

const warningItemStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(251, 191, 36, 0.2)",
  background: "rgba(120, 53, 15, 0.08)",
  marginTop: "8px",
}

const blockerCodeStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#fca5a5",
}

const warningCodeStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#fbbf24",
}

const blockerMsgStyle: CSSProperties = {
  fontSize: "13px",
  color: "#fecaca",
  marginTop: "2px",
}

const warningMsgStyle: CSSProperties = {
  fontSize: "13px",
  color: "#fde68a",
  marginTop: "2px",
}

const NON_BLOCKING_CODES = new Set(["snapshot_stale", "section_missing_claims"])

// ---- Helpers ----

function AdvanceOutcome({ data, onDismiss }: { data: AdvanceResponse; onDismiss: () => void }) {
  if (data.outcome === "blocked") {
    return (
      <div style={outcomeBlockedStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: "14px", fontWeight: 600, color: "#fca5a5" }}>
              推进被阻止于 {data.gate}
            </div>
            <div style={{ fontSize: "13px", color: "#fecaca", marginTop: "4px" }}>
              当前状态：{data.currentState}
            </div>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", fontSize: "18px", padding: "0 4px", lineHeight: 1 }}
          >
            &times;
          </button>
        </div>
        {data.blockers.length > 0 ? (
          <div>
            {data.blockers.map((blocker, i) => {
              const display = resolveBlockerDisplay(blocker)
              const isWarning = NON_BLOCKING_CODES.has(blocker.code)
              return (
                <div key={`${blocker.code}-${i}`} style={isWarning ? warningItemStyle : blockerItemStyle}>
                  <div style={isWarning ? warningCodeStyle : blockerCodeStyle}>{display.label}</div>
                  <div style={isWarning ? warningMsgStyle : blockerMsgStyle}>{display.detail}</div>
                </div>
              )
            })}
          </div>
        ) : null}
      </div>
    )
  }

  return (
    <div style={outcomeAcceptedStyle}>
      <div style={{ fontSize: "14px", fontWeight: 600, color: "#4ade80" }}>
        推进已通过 {data.gate}
      </div>
      <div style={{ fontSize: "13px", color: "#bbf7d0", marginTop: "4px" }}>
        {data.fromState} &rarr; {data.toState}
      </div>
      {data.handle ? (
        <div style={{ fontSize: "12px", color: "#94a3b8", marginTop: "6px" }}>
          任务：{data.handle.jobId}（{data.handle.status}）
        </div>
      ) : null}
    </div>
  )
}

function SystemWorkspacePage({
  projectId,
  systemId,
}: Readonly<{ projectId: string; systemId: string }>) {
  const [selectedGate, setSelectedGate] = useState<GateKey | null>(null)

  const {
    snapshot,
    gateItems,
    isLoading: statusLoading,
    error: statusError,
  } = useProjectStatus(systemId)

  const {
    advance,
    isPending: advancePending,
    data: advanceResult,
    error: advanceError,
    reset: resetAdvance,
  } = useSystemAdvance(systemId)

  const invalidateWorkflow = useWorkflowInvalidation(systemId)

  const { data: systemDetail } = useSystemDetail(systemId)

  const handleInvalidate = useCallback(
    (event: TaskEvent) => {
      if (
        event.type === "workflow.state_changed" ||
        event.type === "gate.passed" ||
        event.type === "gate.blocked" ||
        event.type === "task.succeeded" ||
        event.type === "task.failed"
      ) {
        invalidateWorkflow()
      }
    },
    [invalidateWorkflow],
  )

  function handleAdvance() {
    resetAdvance()
    advance()
  }

  // ---- Navigation Logic ----

  const authoritativeGateKey = snapshot?.currentGate ?? null
  const selectedGateIsValid = selectedGate
    ? gateItems.some((gate) => gate.key === selectedGate)
    : false

  useEffect(() => {
    if (selectedGate && !selectedGateIsValid) {
      setSelectedGate(null)
    }
  }, [selectedGate, selectedGateIsValid])

  const effectiveGateKey = selectedGateIsValid ? selectedGate : authoritativeGateKey
  const isG2 = effectiveGateKey === "G2"
  const gateVisualState = useMemo(() => {
    if (!effectiveGateKey) {
      return "neutral"
    }

    return gateItems.find((gate) => gate.key === effectiveGateKey)?.state ?? "neutral"
  }, [effectiveGateKey, gateItems])



  if (statusLoading) {
    return <div style={emptyStyle}>加载工作流中...</div>
  }

  if (statusError) {
    return <div style={emptyStyle}>加载工作流失败：{statusError.message}</div>
  }

  const latestBlockers = snapshot?.latestBlockers ?? []
  const latestEvent = snapshot?.latestEvent ?? null

  const evidencePanel = isG2 ? null : (
    <EvidenceHub
      snapshot={snapshot}
      latestBlockers={latestBlockers}
      gateKey={selectedGateIsValid ? selectedGate : authoritativeGateKey}
      systemId={systemId}
    />
  )

  const workbenchPanel = (
    <GatePanel
      snapshot={snapshot}
      systemId={systemId}
      gateKey={authoritativeGateKey}
      selectedGate={selectedGateIsValid ? selectedGate : null}
      gateVisualState={gateVisualState}
      latestBlockers={latestBlockers}
      latestEvent={latestEvent}
      systemDetail={systemDetail ?? null}
    />
  )

  const statusTray = (
    <StatusTray
      projectId={projectId}
      systemId={systemId}
      onInvalidate={handleInvalidate}
      onNavigate={setSelectedGate}
    />
  )

  return (
    <MainShell
      gates={gateItems}
      evidencePanel={evidencePanel}
      workbenchPanel={workbenchPanel}
      statusTray={statusTray}
      onGateSelect={setSelectedGate}
      selectedGateKey={selectedGate}
    >
      <div style={headerStyle}>
        <div>
          <div style={titleStyle}>系统工作区</div>
          <div style={subtitleStyle}>
            项目：{projectId} | 体系：{systemId}
          </div>
        </div>
        <button
          type="button"
          style={advancePending ? advanceBtnDisabledStyle : advanceBtnStyle}
          onClick={handleAdvance}
          disabled={advancePending}
        >
          {advancePending ? "推进中..." : "推进 Gate"}
        </button>
      </div>

      {advanceResult ? <AdvanceOutcome data={advanceResult} onDismiss={resetAdvance} /> : null}

      {advanceError ? (
        <div style={{ color: "#f87171", fontSize: "13px", marginBottom: "4px" }}>
          推进失败：{advanceError.message}
        </div>
      ) : null}
    </MainShell>
  )
}

export default function SystemPage() {
  const params = useParams<{ projectId: string; systemId: string }>()
  const { projectId, systemId } = params

  return (
    <WebSocketProvider projectId={projectId} systemId={systemId}>
      <SystemWorkspacePage projectId={projectId} systemId={systemId} />
    </WebSocketProvider>
  )
}
