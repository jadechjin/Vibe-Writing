"use client"

import { useState, type CSSProperties } from "react"
import { TraceableText } from "./TraceableText"

type DraftPreviewProps = Readonly<{
  contentMd: string
  onEdit?: (newContent: string) => void
  onClaimHover?: (claimTag: string | null) => void
}>

const previewStyle: CSSProperties = {
  flex: 1,
  overflowY: "auto",
  padding: "12px",
  fontSize: "13px",
  lineHeight: 1.7,
  color: "#e2e8f0",
  background: "rgba(15,23,42,0.4)",
  borderRadius: "8px",
}

const editStyle: CSSProperties = {
  ...previewStyle,
  fontFamily: "monospace",
  border: "1px solid rgba(148,163,184,0.2)",
  resize: "none",
  outline: "none",
  width: "100%",
  minHeight: "200px",
}

const toggleStyle: CSSProperties = {
  padding: "3px 10px",
  borderRadius: "6px",
  border: "1px solid rgba(148,163,184,0.15)",
  background: "transparent",
  color: "#94a3b8",
  fontSize: "12px",
  cursor: "pointer",
}

export function DraftPreview({ contentMd, onEdit, onClaimHover }: DraftPreviewProps) {
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState(contentMd)

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1 }}>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
        <button style={toggleStyle} onClick={() => setEditing(!editing)}>
          {editing ? "预览" : "编辑"}
        </button>
        {editing && onEdit && (
          <button
            style={{ ...toggleStyle, color: "#10b981" }}
            onClick={() => { onEdit(editContent); setEditing(false) }}
          >
            保存
          </button>
        )}
      </div>
      {editing ? (
        <textarea
          style={editStyle}
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
        />
      ) : (
        <div style={previewStyle}>
          <TraceableText content={contentMd} onClaimHover={onClaimHover} />
        </div>
      )}
    </div>
  )
}
