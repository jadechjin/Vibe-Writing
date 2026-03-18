"use client"

import { useCallback, useState, type CSSProperties } from "react"

import { useDrafts } from "../../../hooks/useDrafts"
import { useValidateAndSaveDraft } from "../../../hooks/useDraftValidation"
import { DraftingChat } from "./DraftingChat"
import { DraftPreview } from "./DraftPreview"

type DraftingWorkspaceProps = Readonly<{
  systemId: string
  sections: Array<{ sectionKey: string; title: string }>
}>

const containerStyle: CSSProperties = {
  display: "flex",
  height: "100%",
  gap: "1px",
  background: "rgba(30,41,59,0.3)",
}

const sidebarStyle: CSSProperties = {
  width: "200px",
  flexShrink: 0,
  overflowY: "auto",
  padding: "8px",
  display: "flex",
  flexDirection: "column",
  gap: "4px",
}

const mainStyle: CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  padding: "8px",
  minWidth: 0,
}

const splitStyle: CSSProperties = {
  display: "flex",
  flex: 1,
  gap: "8px",
  minHeight: 0,
}

export function DraftingWorkspace({ systemId, sections }: DraftingWorkspaceProps) {
  const [activeSection, setActiveSection] = useState(sections[0]?.sectionKey ?? "")
  const { data: drafts } = useDrafts(systemId)
  const validateMutation = useValidateAndSaveDraft(systemId)

  const latestDraft = drafts
    ?.filter((d) => d.sectionKey === activeSection)
    .sort((a, b) => b.version - a.version)[0]

  const handleDraftReady = useCallback(
    (content: string) => {
      validateMutation.mutate({ sectionKey: activeSection, contentMd: content })
    },
    [activeSection, validateMutation],
  )

  const handleManualEdit = useCallback(
    (content: string) => {
      validateMutation.mutate({ sectionKey: activeSection, contentMd: content })
    },
    [activeSection, validateMutation],
  )

  return (
    <div style={containerStyle}>
      <div style={sidebarStyle}>
        <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>章节列表</div>
        {sections.map((sec) => {
          const draft = drafts?.filter((d) => d.sectionKey === sec.sectionKey)
            .sort((a, b) => b.version - a.version)[0]
          const isActive = sec.sectionKey === activeSection
          return (
            <button
              key={sec.sectionKey}
              onClick={() => setActiveSection(sec.sectionKey)}
              style={{
                padding: "6px 10px",
                borderRadius: "6px",
                border: isActive ? "1px solid #3b82f6" : "1px solid transparent",
                background: isActive ? "rgba(59,130,246,0.1)" : "transparent",
                color: isActive ? "#e2e8f0" : "#94a3b8",
                fontSize: "12px",
                textAlign: "left",
                cursor: "pointer",
              }}
            >
              <div>{sec.title}</div>
              <div style={{ fontSize: "10px", color: "#64748b" }}>
                {draft ? `v${draft.version} · ${draft.status}` : "未生成"}
              </div>
            </button>
          )
        })}
      </div>
      <div style={mainStyle}>
        <div style={{ fontSize: "14px", fontWeight: 600, color: "#e2e8f0" }}>
          {sections.find((s) => s.sectionKey === activeSection)?.title ?? activeSection}
        </div>
        <div style={splitStyle}>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
            <DraftingChat
              systemId={systemId}
              sectionKey={activeSection}
              onDraftReady={handleDraftReady}
            />
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
            {latestDraft ? (
              <DraftPreview contentMd={latestDraft.contentMd} onEdit={handleManualEdit} />
            ) : (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748b", fontSize: "13px" }}>
                使用左侧对话生成草稿
              </div>
            )}
          </div>
        </div>
        {validateMutation.data && !validateMutation.data.validationPassed && (
          <div style={{ padding: "8px", background: "rgba(239,68,68,0.1)", borderRadius: "6px", fontSize: "12px", color: "#f87171" }}>
            校验未通过: {validateMutation.data.errors.map((e) => (e as Record<string, unknown>).code).join(", ")}
          </div>
        )}
      </div>
    </div>
  )
}
