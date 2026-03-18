"use client"

import type { CSSProperties } from "react"

import { useDrafts } from "../../hooks/useDrafts"

type G5EvidencePanelProps = Readonly<{ systemId: string }>

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "10px",
  padding: "14px 16px",
  borderRadius: "14px",
  border: "1px solid rgba(148,163,184,0.1)",
  background: "rgba(15,23,42,0.3)",
}

const titleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 700,
  color: "#e2e8f0",
}

const itemStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
  padding: "6px 0",
  borderBottom: "1px solid rgba(148,163,184,0.06)",
}

export function G5EvidencePanel({ systemId }: G5EvidencePanelProps) {
  const { data: drafts } = useDrafts(systemId)

  const sections = new Map<string, { version: number; status: string }>()
  for (const d of drafts ?? []) {
    const existing = sections.get(d.sectionKey)
    if (!existing || d.version > existing.version) {
      sections.set(d.sectionKey, { version: d.version, status: d.status })
    }
  }

  const total = sections.size
  const approved = [...sections.values()].filter((s) => s.status === "approved").length

  return (
    <div style={containerStyle}>
      <div style={titleStyle}>章节草稿进度</div>
      <div style={{ fontSize: "12px", color: "#94a3b8" }}>
        {approved}/{total} 章节已通过审批
      </div>
      {[...sections.entries()].map(([key, info]) => (
        <div key={key} style={itemStyle}>
          {key} — v{info.version} · {info.status}
        </div>
      ))}
    </div>
  )
}
