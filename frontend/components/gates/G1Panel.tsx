import { useState, useEffect, type CSSProperties } from "react"
import { FigurePlanPanel } from "./FigurePlanPanel"
import { AnalysisPanel } from "./AnalysisPanel"
import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import type { SystemDetail } from "../../hooks/useProjects"

type Props = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
  systemDetail: SystemDetail | null
}>

const tabs = [
  { key: "planning", label: "图表规划" },
  { key: "analysis", label: "数据与分析" },
] as const

type TabKey = (typeof tabs)[number]["key"]

function resolveDefaultTab(currentState: string | null): TabKey {
  switch (currentState) {
    case "Data_Pending":
    case "Data_Uploaded":
      return "analysis"
    default:
      return "planning"
  }
}

const tabBarStyle: CSSProperties = {
  display: "flex",
  gap: "2px",
  padding: "4px",
  borderRadius: "12px",
  background: "rgba(15, 23, 42, 0.6)",
  border: "1px solid rgba(148, 163, 184, 0.18)",
  marginBottom: "16px",
}

const tabStyle: CSSProperties = {
  flex: 1,
  padding: "8px 16px",
  borderRadius: "8px",
  border: "none",
  background: "transparent",
  color: "#94a3b8",
  fontSize: "13px",
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.15s ease",
}

const activeTabStyle: CSSProperties = {
  ...tabStyle,
  background: "rgba(59, 130, 246, 0.18)",
  color: "#93c5fd",
  border: "1px solid rgba(59, 130, 246, 0.35)",
}

export function G1Panel({ snapshot, blockers, systemId, systemDetail }: Props) {
  const currentState = snapshot?.currentState ?? null
  const [activeTab, setActiveTab] = useState<TabKey>(resolveDefaultTab(currentState))

  useEffect(() => {
    if (currentState === "Figure_Plan_Ready" || currentState === "Data_Pending" || currentState === "Data_Uploaded") {
      setActiveTab("analysis")
    }
  }, [currentState])

  const panelProps = { snapshot, blockers, systemId, systemDetail }

  return (
    <div>
      <div style={tabBarStyle}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            style={activeTab === tab.key ? activeTabStyle : tabStyle}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {activeTab === "planning" ? (
        <FigurePlanPanel {...panelProps} />
      ) : (
        <AnalysisPanel {...panelProps} />
      )}
    </div>
  )
}
