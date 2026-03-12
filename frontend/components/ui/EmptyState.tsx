import type { CSSProperties, ReactNode } from "react"
import { gateTheme } from "@/styles/gate-theme"

interface EmptyStateProps {
  text: string
  icon?: ReactNode
  style?: CSSProperties
}

export function EmptyState({ text, icon, style }: EmptyStateProps) {
  return (
    <div style={{ ...gateTheme.emptyState, ...style }}>
      {icon && <div style={{ marginBottom: "8px" }}>{icon}</div>}
      {text}
    </div>
  )
}
