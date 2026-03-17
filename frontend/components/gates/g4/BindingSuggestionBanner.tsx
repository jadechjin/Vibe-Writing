"use client"

import type { CSSProperties } from "react"
import type { BindingSuggestion } from "../../../types/g4"
import { ActionButton } from "../../ui/ActionButton"

type Props = {
  suggestions: BindingSuggestion[]
  assetNameById: Map<string, string>
  onConfirm: (assetId: string) => void
  isPending?: boolean
}

const bannerStyle: CSSProperties = {
  padding: "10px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(96, 165, 250, 0.2)",
  background: "rgba(96, 165, 250, 0.06)",
}

const titleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#93c5fd",
  marginBottom: "8px",
}

const itemStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "8px",
  padding: "6px 0",
  borderBottom: "1px solid rgba(148, 163, 184, 0.08)",
}

export function BindingSuggestionBanner({ suggestions, assetNameById, onConfirm, isPending }: Props) {
  if (suggestions.length === 0) return null

  return (
    <div style={bannerStyle}>
      <div style={titleStyle}>绑定建议</div>
      {suggestions.map((s) => (
        <div key={s.assetId} style={itemStyle}>
          <div>
            <div style={{ fontSize: "12px", color: "#e2e8f0" }}>
              {assetNameById.get(s.assetId) ?? s.assetId.slice(0, 8)}
            </div>
            <div style={{ fontSize: "11px", color: "#64748b" }}>{s.reason}</div>
          </div>
          <ActionButton
            label="确认绑定"
            onClick={() => onConfirm(s.assetId)}
            disabled={isPending}
            variant="secondary"
            style={{ padding: "4px 10px", fontSize: "11px" }}
          />
        </div>
      ))}
    </div>
  )
}
