"use client"

import type { CSSProperties } from "react"

import { useFigurePlans, type FigurePlanDetail } from "../../hooks/useFigurePlan"

export type G1EvidencePanelProps = Readonly<{
  systemId: string
}>

// aligned with backend gates/service.py:375
function isConfirmedStatus(status: string | null | undefined): boolean {
  const s = (status ?? "").trim().toLowerCase()
  return s === "confirmed" || s === "approved"
}

// aligned with backend gates/service.py:90 _latest_by_version
function latestByFigureNo(plans: readonly FigurePlanDetail[]): FigurePlanDetail[] {
  const latest = new Map<string, FigurePlanDetail>()
  for (const plan of plans) {
    const current = latest.get(plan.figureNo)
    if (!current || plan.version > current.version) {
      latest.set(plan.figureNo, plan)
    }
  }
  return Array.from(latest.values())
}

function parseFigureNumber(figureNo: string): number {
  const match = figureNo.match(/\d+/)
  return match ? parseInt(match[0], 10) : 0
}

// -- Styles --

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
}

const titleStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 700,
  color: "#f8fafc",
}

const statsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, 1fr)",
  gap: "10px",
}

const statsCardStyle: CSSProperties = {
  padding: "10px",
  borderRadius: "10px",
  background: "rgba(15, 23, 42, 0.4)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  textAlign: "center",
}

const statsLabelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  marginBottom: "4px",
}

const readyHintStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "8px",
  fontSize: "13px",
  lineHeight: 1.5,
  background: "rgba(34, 197, 94, 0.1)",
  border: "1px solid rgba(34, 197, 94, 0.2)",
  color: "#4ade80",
}

const listStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  marginTop: "4px",
}

const itemStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
  padding: "10px 12px",
  borderRadius: "10px",
  background: "rgba(15, 23, 42, 0.5)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
}

const itemInfoStyle: CSSProperties = {
  flex: 1,
  minWidth: 0,
}

const itemTitleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#f1f5f9",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
}

const itemDescStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
  marginTop: "2px",
  whiteSpace: "nowrap",
  overflow: "hidden",
  textOverflow: "ellipsis",
}

// -- Component --

export function G1EvidencePanel({ systemId }: G1EvidencePanelProps) {
  const { data, isLoading, error } = useFigurePlans(systemId)

  if (isLoading) {
    return <div style={{ fontSize: "12px", color: "#64748b" }}>加载 Figure Plan 中...</div>
  }

  if (error) {
    return (
      <div style={{ fontSize: "12px", color: "#f87171" }}>
        加载失败：{error instanceof Error ? error.message : "未知错误"}
      </div>
    )
  }

  const allPlans = data ?? []
  const latestPlans = latestByFigureNo(allPlans).sort(
    (a, b) => parseFigureNumber(a.figureNo) - parseFigureNumber(b.figureNo),
  )

  if (latestPlans.length === 0) {
    return (
      <div style={{ fontSize: "12px", color: "#64748b" }}>
        尚未生成图表规划，请在右侧工作台生成。
      </div>
    )
  }

  const readyCount = latestPlans.filter((p) => isConfirmedStatus(p.status)).length
  const pendingCount = latestPlans.length - readyCount
  const isAllReady = latestPlans.length > 0 && pendingCount === 0

  return (
    <div style={containerStyle}>
      <div style={titleStyle}>图表规划进度</div>

      <div style={statsGridStyle}>
        <div style={statsCardStyle}>
          <div style={statsLabelStyle}>全部</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#e2e8f0" }}>
            {latestPlans.length}
          </div>
        </div>
        <div style={statsCardStyle}>
          <div style={statsLabelStyle}>已确认</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#4ade80" }}>
            {readyCount}
          </div>
        </div>
        <div style={statsCardStyle}>
          <div style={statsLabelStyle}>待确认</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#fb923c" }}>
            {pendingCount}
          </div>
        </div>
      </div>

      {isAllReady ? (
        <div style={readyHintStyle}>所有图表规划已确认，可推进至 G2</div>
      ) : (
        <div style={{ fontSize: "12px", color: "#fb923c", padding: "0 4px" }}>
          还差 {pendingCount} 个确认后可推进至 G2
        </div>
      )}

      <div style={listStyle}>
        {latestPlans.map((p) => {
          const confirmed = isConfirmedStatus(p.status)
          return (
            <div key={p.id} style={itemStyle}>
              <div style={itemInfoStyle}>
                <div style={itemTitleStyle}>
                  {p.figureNo}: {p.title}
                </div>
                <div style={itemDescStyle}>
                  {p.sectionKey ?? "未关联章节"} · {p.briefText || p.claimText}
                </div>
              </div>
              <div
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "6px",
                  background: confirmed
                    ? "rgba(34, 197, 94, 0.15)"
                    : "rgba(251, 146, 60, 0.15)",
                  color: confirmed ? "#4ade80" : "#fb923c",
                  border: `1px solid ${confirmed ? "rgba(34, 197, 94, 0.2)" : "rgba(251, 146, 60, 0.2)"}`,
                }}
              >
                {confirmed ? "已确认" : "待确认"}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
