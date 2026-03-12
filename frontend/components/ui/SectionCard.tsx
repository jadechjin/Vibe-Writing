import type { CSSProperties, ReactNode } from "react"
import { gateTheme } from "@/styles/gate-theme"

interface SectionCardProps {
  title: string | ReactNode
  description?: string
  children: ReactNode
  headerExtra?: ReactNode
  style?: CSSProperties
}

export function SectionCard({ title, description, children, headerExtra, style }: SectionCardProps) {
  return (
    <div style={{ ...gateTheme.sectionCard, ...style }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={gateTheme.title}>{title}</div>
        {headerExtra}
      </div>
      {description && <div style={gateTheme.desc}>{description}</div>}
      {children}
    </div>
  )
}
