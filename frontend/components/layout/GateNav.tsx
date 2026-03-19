import type { CSSProperties } from "react"
import type { GateKey } from "../../lib/gateMapping"

export type GateVisualStatus =
  | "neutral"
  | "locked"
  | "active"
  | "passed"
  | "pending"

export type GateNavItem = Readonly<{
  key: string
  label: string
  title: string
  summary: string
  state: GateVisualStatus
}>

type GateStyleToken = Readonly<{
  badge: string
  borderColor: string
  background: string
  textColor: string
  accent: string
}>

const gateStateTokens: Record<GateVisualStatus, GateStyleToken> = {
  neutral: {
    badge: "等待数据",
    borderColor: "rgba(148, 163, 184, 0.24)",
    background: "rgba(15, 23, 42, 0.62)",
    textColor: "#cbd5e1",
    accent: "#64748b",
  },
  locked: {
    badge: "已锁定",
    borderColor: "rgba(120, 139, 165, 0.35)",
    background: "rgba(15, 23, 42, 0.78)",
    textColor: "#8da2bf",
    accent: "#475569",
  },
  active: {
    badge: "进行中",
    borderColor: "rgba(59, 130, 246, 0.72)",
    background: "rgba(30, 64, 175, 0.18)",
    textColor: "#dbeafe",
    accent: "#3b82f6",
  },
  passed: {
    badge: "已通过",
    borderColor: "rgba(34, 197, 94, 0.6)",
    background: "rgba(20, 83, 45, 0.3)",
    textColor: "#dcfce7",
    accent: "#16a34a",
  },
  pending: {
    badge: "待处理",
    borderColor: "rgba(249, 115, 22, 0.58)",
    background: "rgba(154, 52, 18, 0.18)",
    textColor: "#ffedd5",
    accent: "#f97316",
  },
}

const headerStyle: CSSProperties = {
  position: "sticky",
  top: 0,
  zIndex: 40,
  borderBottom: "1px solid rgba(148, 163, 184, 0.18)",
  background: "rgba(7, 13, 24, 0.88)",
  backdropFilter: "blur(18px)",
}

const headerInnerStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  alignItems: "center",
  gap: "16px",
  maxWidth: "1440px",
  margin: "0 auto",
  padding: "16px 24px",
}

const titleBlockStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "4px",
  minWidth: "180px",
}

const eyebrowStyle: CSSProperties = {
  fontSize: "11px",
  fontWeight: 700,
  letterSpacing: "0.12em",
  textTransform: "uppercase",
  color: "#93c5fd",
}

const titleStyle: CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#f8fafc",
}

const subtitleStyle: CSSProperties = {
  fontSize: "13px",
  color: "#94a3b8",
}

const gateListStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(4, minmax(132px, 1fr))",
  gap: "12px",
  listStyle: "none",
  margin: 0,
  padding: 0,
  flex: "1 1 720px",
}

const gateCardStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "10px",
  minHeight: "92px",
  padding: "12px 14px",
  borderRadius: "16px",
  border: "1px solid transparent",
  boxSizing: "border-box",
}

const gateCardHeaderStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: "8px",
}

const gateKeyStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  minWidth: "42px",
  padding: "4px 10px",
  borderRadius: "999px",
  fontSize: "12px",
  fontWeight: 700,
  color: "#f8fafc",
}

const gateBadgeStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "4px 10px",
  borderRadius: "999px",
  border: "1px solid currentColor",
  fontSize: "11px",
  fontWeight: 700,
  letterSpacing: "0.02em",
}

const gateTitleStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 700,
  color: "#e2e8f0",
}

const gateSummaryStyle: CSSProperties = {
  fontSize: "12px",
  lineHeight: 1.45,
  color: "#94a3b8",
}

export const DEFAULT_GATE_PLACEHOLDERS: readonly GateNavItem[] = [
  {
    key: "G0",
    label: "G0",
    title: "体系定义",
    summary: "等待项目与实验体系上下文注入。",
    state: "neutral",
  },
  {
    key: "G1",
    label: "G1",
    title: "图表与分析",
    summary: "等待 gate 状态数据接入。",
    state: "neutral",
  },
  {
    key: "G2",
    label: "G2",
    title: "证据与提纲",
    summary: "等待 gate 状态数据接入。",
    state: "neutral",
  },
  {
    key: "G3",
    label: "G3",
    title: "写作审批",
    summary: "等待 gate 状态数据接入。",
    state: "neutral",
  },
]

export function GateNav({
  gates,
  onGateSelect,
  selectedGateKey,
}: {
  gates: readonly GateNavItem[]
  onGateSelect?: (gateKey: GateKey) => void
  selectedGateKey?: GateKey | null
}) {
  return (
    <header style={headerStyle}>
      <div style={headerInnerStyle}>
        <div style={titleBlockStyle}>
          <span style={eyebrowStyle}>门禁工作流</span>
          <strong style={titleStyle}>论文工作台</strong>
          <span style={subtitleStyle}>G0–G3 门禁驱动的实验体系推进</span>
        </div>

        <nav aria-label="Gate 导航" style={{ flex: "1 1 auto" }}>
          <ol style={gateListStyle}>
            {gates.map((gate) => {
              const token = gateStateTokens[gate.state]
              const isSelected = selectedGateKey === gate.key && selectedGateKey !== null
              const isActive = gate.state === "active"

              return (
                <li
                  key={gate.key}
                  role="button"
                  tabIndex={0}
                  aria-current={isActive ? "step" : undefined}
                  aria-pressed={isSelected}
                  onClick={() => onGateSelect?.(gate.key as GateKey)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      onGateSelect?.(gate.key as GateKey)
                    }
                  }}
                  style={{
                    ...gateCardStyle,
                    background: token.background,
                    borderColor: isSelected ? "rgba(251, 191, 36, 0.7)" : token.borderColor,
                    borderStyle: isSelected ? "dashed" : "solid",
                    boxShadow: isActive && !isSelected
                      ? `0 0 0 1px ${token.accent}`
                      : undefined,
                    cursor: "pointer",
                  }}
                >
                  <div style={gateCardHeaderStyle}>
                    <span style={{ ...gateKeyStyle, background: token.accent }}>
                      {gate.label}
                    </span>
                    <span
                      style={{
                        ...gateBadgeStyle,
                        color: token.textColor,
                      }}
                    >
                      {token.badge}
                    </span>
                  </div>
                  <span style={gateTitleStyle}>{gate.title}</span>
                  <span style={gateSummaryStyle}>{gate.summary}</span>
                </li>
              )
            })}
          </ol>
        </nav>
      </div>
    </header>
  )
}
