"use client"

import { useState, type CSSProperties } from "react"

type Citation = {
  id?: string
  title?: string
  authors?: string
  year?: number
  doi?: string
  url?: string
  snippets?: Array<{ source?: string; text?: string }>
}

type AnalysisResult = {
  schema_version?: string
  narrative?: { summary_cn?: string; detail_cn?: string }
  citations?: Citation[]
  confidence?: { overall?: number }
  status?: { review_state?: string }
}

type LiteraturePanelProps = Readonly<{
  analysisResult: AnalysisResult | null
  onConfirm?: () => void
  isConfirming?: boolean
}>

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "10px",
  flex: 1,
  minHeight: 0,
  overflow: "auto",
}

const sectionTitleStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 700,
  color: "#94a3b8",
  textTransform: "uppercase",
  letterSpacing: "0.05em",
}

const summaryStyle: CSSProperties = {
  fontSize: "12px",
  color: "#e2e8f0",
  lineHeight: 1.6,
  padding: "8px 10px",
  borderRadius: "8px",
  background: "rgba(15,23,42,0.4)",
  border: "1px solid rgba(148,163,184,0.08)",
}

const citationItemStyle: CSSProperties = {
  padding: "8px 10px",
  borderRadius: "8px",
  background: "rgba(15,23,42,0.4)",
  border: "1px solid rgba(148,163,184,0.08)",
  fontSize: "12px",
  color: "#cbd5e1",
  lineHeight: 1.5,
}

const citationNumStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 700,
  color: "#60a5fa",
  marginRight: "6px",
}

const linkStyle: CSSProperties = {
  color: "#60a5fa",
  textDecoration: "none",
  fontSize: "11px",
}

const sourceTagStyle: CSSProperties = {
  fontSize: "9px",
  fontWeight: 600,
  padding: "1px 5px",
  borderRadius: "4px",
  background: "rgba(148,163,184,0.1)",
  color: "#94a3b8",
  marginLeft: "6px",
}

const confidenceBarBg: CSSProperties = {
  height: "6px",
  borderRadius: "3px",
  background: "rgba(148,163,184,0.15)",
  overflow: "hidden",
}

const reviewBadgeColors: Record<string, { bg: string; color: string; border: string }> = {
  auto_pass: { bg: "rgba(34,197,94,0.15)", color: "#4ade80", border: "rgba(34,197,94,0.2)" },
  needs_review: { bg: "rgba(251,191,36,0.15)", color: "#fbbf24", border: "rgba(251,191,36,0.2)" },
  rejected: { bg: "rgba(248,113,113,0.15)", color: "#f87171", border: "rgba(248,113,113,0.2)" },
}

const reviewLabels: Record<string, string> = {
  auto_pass: "自动通过",
  needs_review: "建议复核",
  rejected: "已拒绝",
}

const btnBase: CSSProperties = {
  padding: "6px 14px",
  borderRadius: "8px",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
}

const confirmBtnStyle: CSSProperties = {
  ...btnBase,
  border: "1px solid rgba(74,222,128,0.5)",
  background: "rgba(22,101,52,0.15)",
  color: "#4ade80",
}

const btnDisabled: CSSProperties = { opacity: 0.5, cursor: "not-allowed" }

const emptyStyle: CSSProperties = {
  fontSize: "12px",
  color: "#64748b",
  textAlign: "center",
  padding: "16px 0",
}

export function LiteraturePanel({ analysisResult, onConfirm, isConfirming }: LiteraturePanelProps) {
  const [isEditing, setIsEditing] = useState(false)

  if (!analysisResult) {
    return <div style={emptyStyle}>尚无分析结果。请先执行 AI 分析。</div>
  }

  const narrative = analysisResult.narrative
  const citations = analysisResult.citations ?? []
  const confidence = analysisResult.confidence?.overall
  const reviewState = analysisResult.status?.review_state
  const reviewStyle = reviewState ? reviewBadgeColors[reviewState] : null

  return (
    <div style={containerStyle}>
      {/* Summary */}
      {narrative?.summary_cn ? (
        <>
          <div style={sectionTitleStyle}>分析摘要</div>
          <div style={summaryStyle}>{narrative.summary_cn}</div>
        </>
      ) : null}

      {/* Confidence */}
      {confidence != null ? (
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <div style={sectionTitleStyle}>置信度</div>
          <div style={{ ...confidenceBarBg, flex: 1 }}>
            <div style={{
              height: "100%",
              borderRadius: "3px",
              width: `${Math.min(confidence * 100, 100)}%`,
              background: confidence >= 0.85 ? "#4ade80" : confidence >= 0.6 ? "#fbbf24" : "#f87171",
            }} />
          </div>
          <span style={{ fontSize: "11px", color: "#e2e8f0", fontWeight: 600 }}>
            {(confidence * 100).toFixed(0)}%
          </span>
        </div>
      ) : null}

      {/* Review State */}
      {reviewState && reviewStyle ? (
        <span style={{
          fontSize: "11px", fontWeight: 600, padding: "2px 8px", borderRadius: "6px",
          alignSelf: "flex-start",
          background: reviewStyle.bg, color: reviewStyle.color,
          border: `1px solid ${reviewStyle.border}`,
        }}>
          {reviewLabels[reviewState] ?? reviewState}
        </span>
      ) : null}

      {/* Citations */}
      {citations.length > 0 ? (
        <>
          <div style={sectionTitleStyle}>文献引用 ({citations.length})</div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {citations.map((c, i) => (
              <div key={c.id ?? i} style={citationItemStyle}>
                <span style={citationNumStyle}>[{i + 1}]</span>
                {c.authors ? <span>{c.authors} </span> : null}
                {c.year ? <span>({c.year}) </span> : null}
                {c.title ? <span style={{ fontWeight: 600 }}>{c.title}</span> : null}
                {c.doi ? (
                  <a href={`https://doi.org/${c.doi}`} target="_blank" rel="noopener noreferrer" style={linkStyle}>
                    {" "}DOI
                  </a>
                ) : c.url ? (
                  <a href={c.url} target="_blank" rel="noopener noreferrer" style={linkStyle}> Link</a>
                ) : null}
                {c.snippets?.map((s, si) => (
                  <span key={si} style={sourceTagStyle}>{s.source ?? "unknown"}</span>
                ))}
              </div>
            ))}
          </div>
        </>
      ) : null}

      {/* Actions */}
      <div style={{ display: "flex", gap: "8px", marginTop: "8px", flexShrink: 0 }}>
        {!isEditing ? (
          <button type="button" style={{ ...btnBase, border: "1px solid rgba(96,165,250,0.5)",
            background: "rgba(30,64,175,0.15)", color: "#60a5fa" }}
            onClick={() => setIsEditing(true)}>
            编辑分析
          </button>
        ) : (
          <button type="button" style={{ ...btnBase, border: "1px solid rgba(148,163,184,0.2)",
            background: "transparent", color: "#94a3b8" }}
            onClick={() => setIsEditing(false)}>
            取消编辑
          </button>
        )}
        {onConfirm ? (
          <button type="button"
            style={isConfirming ? { ...confirmBtnStyle, ...btnDisabled } : confirmBtnStyle}
            disabled={isConfirming}
            onClick={onConfirm}>
            {isConfirming ? "确认中..." : "确认分析"}
          </button>
        ) : null}
      </div>
    </div>
  )
}
