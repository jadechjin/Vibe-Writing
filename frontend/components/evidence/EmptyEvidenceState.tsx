import type { CSSProperties } from "react"

// ---- Props ----

export type EmptyEvidenceStateProps = Readonly<{
  title: string
  description: string
  nextAction?: string
  hint?: string
}>

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
  padding: "28px 20px",
  borderRadius: "18px",
  border: "1px dashed rgba(96, 165, 250, 0.35)",
  background: "rgba(30, 41, 59, 0.38)",
  textAlign: "center",
}

const titleStyle: CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  color: "#e2e8f0",
}

const descriptionStyle: CSSProperties = {
  fontSize: "14px",
  lineHeight: 1.6,
  color: "#94a3b8",
}

const nextActionStyle: CSSProperties = {
  display: "inline-block",
  padding: "8px 18px",
  borderRadius: "12px",
  border: "1px solid rgba(59, 130, 246, 0.5)",
  background: "rgba(30, 64, 175, 0.15)",
  fontSize: "13px",
  fontWeight: 600,
  color: "#60a5fa",
}

const hintStyle: CSSProperties = {
  fontSize: "12px",
  lineHeight: 1.5,
  color: "#64748b",
  fontStyle: "italic",
}

// ---- Component ----

export function EmptyEvidenceState({
  title,
  description,
  nextAction,
  hint,
}: EmptyEvidenceStateProps) {
  return (
    <div style={containerStyle}>
      <div style={titleStyle}>{title}</div>
      <div style={descriptionStyle}>{description}</div>
      {nextAction ? <div style={nextActionStyle}>{nextAction}</div> : null}
      {hint ? <div style={hintStyle}>{hint}</div> : null}
    </div>
  )
}
