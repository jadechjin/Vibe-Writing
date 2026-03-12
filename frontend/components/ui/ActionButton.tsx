import type { CSSProperties } from "react"
import { gateTheme } from "@/styles/gate-theme"

interface ActionButtonProps {
  label: string
  onClick: () => void
  disabled?: boolean
  isPending?: boolean
  variant?: "primary" | "secondary" | "danger"
  style?: CSSProperties
}

const variantStyles: Record<string, CSSProperties> = {
  primary: gateTheme.actionBtn,
  secondary: {
    ...gateTheme.actionBtn,
    border: "1px solid rgba(148, 163, 184, 0.3)",
    background: "rgba(30, 41, 59, 0.4)",
    color: "#94a3b8",
  },
  danger: {
    ...gateTheme.actionBtn,
    border: "1px solid rgba(239, 68, 68, 0.5)",
    background: "rgba(127, 29, 29, 0.15)",
    color: "#f87171",
  },
}

export function ActionButton({
  label,
  onClick,
  disabled = false,
  isPending = false,
  variant = "primary",
  style,
}: ActionButtonProps) {
  const isDisabled = disabled || isPending
  return (
    <button
      onClick={onClick}
      disabled={isDisabled}
      style={{
        ...variantStyles[variant],
        opacity: isDisabled ? 0.5 : 1,
        cursor: isDisabled ? "not-allowed" : "pointer",
        ...style,
      }}
    >
      {isPending ? "..." : label}
    </button>
  )
}
