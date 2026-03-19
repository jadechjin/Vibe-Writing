import { useState, useEffect, type CSSProperties } from "react"
import { ManifestPanel } from "./ManifestPanel"
import { EvidenceMatrixPanel } from "./EvidenceMatrixPanel"
import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import type { SystemDetail } from "../../hooks/useProjects"

type Props = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
  systemDetail: SystemDetail | null
}>

const tabs = [
  { key: "audit", label: "资产审计" },
  { key: "evidence", label: "证据与提纲" },
] as const

type TabKey = (typeof tabs)[number]["key"]

function resolveDefaultTab(currentState: string | null): TabKey {
  switch (currentState) {
    case "Assets_Confirmed":
    case "Evidence_Matrix_Ready":
      return "evidence"
    default:
      return "audit"
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

export function G2Panel({ snapshot, blockers, systemId, systemDetail }: Props) {
  const currentState = snapshot?.currentState ?? null
  const [activeTab, setActiveTab] = useState<TabKey>(resolveDefaultTab(currentState))

  useEffect(() => {
    if (currentState === "Assets_Confirmed" || currentState === "Evidence_Matrix_Ready") {
      setActiveTab("evidence")
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
      {activeTab === "audit" ? (
        <ManifestPanel {...panelProps} />
      ) : (
        <EvidenceMatrixPanel {...panelProps} />
      )}
    </div>
  )
}
