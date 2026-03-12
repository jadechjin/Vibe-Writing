"use client"

import { useState, type CSSProperties, type ReactNode } from "react"

import { SystemDefinitionForm } from "./SystemDefinitionForm"
import type { SystemDetail } from "../../hooks/useProjects"
import type { SystemUpdateInput } from "../../hooks/useSystem"
import type { Blocker } from "../../hooks/useProjectStatus"
import { LiteratureTab } from "./g0/LiteratureTab"
import { SkeletonTab } from "./g0/SkeletonTab"

// ---- Props ----

export type G0WorkbenchProps = Readonly<{
  systemId: string
  systemDetail: SystemDetail | null
  blockers: Blocker[]
  onSave: (data: SystemUpdateInput) => void
  isReadOnly: boolean
  isUpdating?: boolean
}>

// ---- Tab config ----

type TabKey = "literature" | "skeleton" | "fields"

type TabDef = { key: TabKey; label: string }

const TABS: TabDef[] = [
  { key: "literature", label: "模板文献" },
  { key: "skeleton", label: "结构骨架" },
  { key: "fields", label: "体系字段" },
]

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
}

const tabBarStyle: CSSProperties = {
  display: "flex",
  gap: "4px",
  borderBottom: "1px solid rgba(148, 163, 184, 0.15)",
  paddingBottom: "0",
}

const tabBaseStyle: CSSProperties = {
  padding: "8px 16px",
  fontSize: "13px",
  fontWeight: 600,
  color: "#64748b",
  background: "transparent",
  border: "none",
  borderBottomWidth: "2px",
  borderBottomStyle: "solid",
  borderBottomColor: "transparent",
  cursor: "pointer",
  transition: "color 0.15s, border-color 0.15s",
}

const tabActiveStyle: CSSProperties = {
  ...tabBaseStyle,
  color: "#f8fafc",
  borderBottomColor: "#fb923c",
}

const tabContentStyle: CSSProperties = {
  minHeight: "120px",
}

// ---- Component ----

export function G0Workbench({
  systemId,
  systemDetail,
  blockers,
  onSave,
  isReadOnly,
  isUpdating,
}: G0WorkbenchProps) {
  const [activeTab, setActiveTab] = useState<TabKey>("skeleton")

  function renderTab(): ReactNode {
    switch (activeTab) {
      case "literature":
        return <LiteratureTab systemId={systemId} isReadOnly={isReadOnly} />
      case "skeleton":
        return <SkeletonTab systemId={systemId} isReadOnly={isReadOnly} />
      case "fields":
        return (
          <SystemDefinitionForm
            initialData={systemDetail}
            blockers={isReadOnly ? [] : blockers}
            onSave={onSave}
            isReadOnly={isReadOnly}
            isUpdating={isUpdating}
          />
        )
      default:
        return null
    }
  }

  return (
    <div style={containerStyle}>
      <div style={tabBarStyle}>
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            style={activeTab === tab.key ? tabActiveStyle : tabBaseStyle}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div style={tabContentStyle}>{renderTab()}</div>
    </div>
  )
}
