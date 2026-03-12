import type { CSSProperties } from "react"

export const gateTheme: Record<string, CSSProperties> = {
  panel: {
    display: "flex",
    flexDirection: "column",
    gap: "14px",
  },
  sectionCard: {
    padding: "16px",
    borderRadius: "14px",
    border: "1px solid rgba(148, 163, 184, 0.15)",
    background: "rgba(30, 41, 59, 0.38)",
  },
  title: {
    fontSize: "15px",
    fontWeight: 700,
    color: "#f8fafc",
    marginBottom: "8px",
  },
  desc: {
    fontSize: "13px",
    lineHeight: 1.6,
    color: "#94a3b8",
  },
  actionBtn: {
    padding: "8px 18px",
    borderRadius: "10px",
    border: "1px solid rgba(249, 115, 22, 0.5)",
    background: "rgba(154, 52, 18, 0.15)",
    fontSize: "13px",
    fontWeight: 600,
    color: "#fb923c",
    cursor: "pointer",
    alignSelf: "flex-start",
  },
  statusBadge: {
    fontSize: "10px",
    padding: "2px 6px",
    borderRadius: "4px",
    background: "rgba(249, 115, 22, 0.1)",
    color: "#fb923c",
    fontWeight: 600,
  },
  emptyState: {
    padding: "20px",
    textAlign: "center",
    color: "#64748b",
    fontSize: "13px",
    fontStyle: "italic",
  },
  fieldGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  input: {
    width: "100%",
    padding: "9px 10px",
    borderRadius: "10px",
    border: "1px solid rgba(148, 163, 184, 0.18)",
    background: "rgba(15, 23, 42, 0.6)",
    color: "#e2e8f0",
    fontSize: "13px",
    outline: "none",
  },
}
