"use client"

import { createPortal } from "react-dom"
import type { CSSProperties } from "react"

import { ActionButton } from "../../ui/ActionButton"
import type { G4IssueAction, G4IssueDetail } from "./issueDetails"

type Props = Readonly<{
  issue: G4IssueDetail | null
  isOpen: boolean
  onClose: () => void
  onAction: (action: G4IssueAction) => void
}>

const overlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(2, 6, 23, 0.55)",
  zIndex: 999,
}

const panelStyle: CSSProperties = {
  position: "fixed",
  top: "0",
  right: "0",
  width: "min(480px, 92vw)",
  height: "100vh",
  padding: "24px",
  background: "rgba(15, 23, 42, 0.98)",
  borderLeft: "1px solid rgba(148, 163, 184, 0.18)",
  boxShadow: "-12px 0 40px rgba(2, 6, 23, 0.35)",
  zIndex: 1000,
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: "18px",
}

const titleStyle: CSSProperties = { fontSize: "18px", fontWeight: 700, color: "#f8fafc" }
const summaryStyle: CSSProperties = { fontSize: "13px", lineHeight: 1.7, color: "#cbd5e1" }
const codeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  padding: "4px 10px",
  borderRadius: "999px",
  background: "rgba(30, 41, 59, 0.8)",
  border: "1px solid rgba(148, 163, 184, 0.18)",
  color: "#94a3b8",
  fontSize: "12px",
}
const sectionStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "10px" }
const sectionTitleStyle: CSSProperties = { fontSize: "13px", fontWeight: 700, color: "#f8fafc" }
const metricStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  background: "rgba(15, 23, 42, 0.55)",
  border: "1px solid rgba(148, 163, 184, 0.12)",
  fontSize: "13px",
  color: "#e2e8f0",
}
const listStyle: CSSProperties = { margin: 0, paddingLeft: "18px", color: "#cbd5e1", fontSize: "13px", lineHeight: 1.7 }
const chipRowStyle: CSSProperties = { display: "flex", gap: "8px", flexWrap: "wrap" }
const chipStyle: CSSProperties = {
  padding: "4px 10px",
  borderRadius: "999px",
  background: "rgba(248, 113, 113, 0.12)",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  color: "#fca5a5",
  fontSize: "12px",
}
const actionRowStyle: CSSProperties = { display: "flex", gap: "8px", flexWrap: "wrap" }
const closeButtonStyle: CSSProperties = {
  alignSelf: "flex-end",
  border: "none",
  background: "transparent",
  color: "#94a3b8",
  cursor: "pointer",
  fontSize: "13px",
}

export function G4IssueDetailPanel({ issue, isOpen, onClose, onAction }: Props) {
  if (!isOpen || !issue) return null

  return createPortal(
    <>
      <div style={overlayStyle} onClick={onClose} />
      <aside style={panelStyle} aria-label="G4 错误详情">
        <button type="button" style={closeButtonStyle} onClick={onClose}>
          关闭
        </button>
        <div style={titleStyle}>{issue.title}</div>
        <div style={summaryStyle}>{issue.summary}</div>
        <div style={codeStyle}>{issue.code}</div>

        <section style={sectionStyle}>
          <div style={sectionTitleStyle}>冲突计数</div>
          {issue.metrics.map((metric) => (
            <div key={metric.label} style={metricStyle}>
              {metric.label}：{metric.value}
            </div>
          ))}
        </section>

        <section style={sectionStyle}>
          <div style={sectionTitleStyle}>影响说明</div>
          <ul style={listStyle}>
            {issue.impactItems.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>

        <section style={sectionStyle}>
          <div style={sectionTitleStyle}>受影响章节</div>
          {issue.sectionsAffected.length > 0 ? (
            <div style={chipRowStyle}>
              {issue.sectionsAffected.map((section) => (
                <span key={section} style={chipStyle}>
                  {section}
                </span>
              ))}
            </div>
          ) : (
            <div style={summaryStyle}>当前响应未返回受影响章节。</div>
          )}
        </section>

        <section style={sectionStyle}>
          <div style={sectionTitleStyle}>推荐动作</div>
          <div style={actionRowStyle}>
            {issue.actions.map((action) => (
              <ActionButton
                key={action.id}
                label={action.label}
                onClick={() => onAction(action)}
                variant={action.variant ?? "secondary"}
                style={{ padding: "6px 12px", fontSize: "12px" }}
              />
            ))}
          </div>
        </section>
      </aside>
    </>,
    document.body,
  )
}
