import type { CSSProperties } from "react"
import { gateTheme } from "@/styles/gate-theme"

type Variant = "pending" | "success" | "warning" | "error" | "auto"

const variantColors: Record<Exclude<Variant, "auto">, CSSProperties> = {
  pending: { background: "rgba(249, 115, 22, 0.1)", color: "#fb923c" },
  success: { background: "rgba(34, 197, 94, 0.1)", color: "#4ade80" },
  warning: { background: "rgba(234, 179, 8, 0.1)", color: "#facc15" },
  error: { background: "rgba(239, 68, 68, 0.1)", color: "#f87171" },
}

function inferVariant(status: string): Exclude<Variant, "auto"> {
  const s = status.toLowerCase()
  if (["approved", "confirmed", "succeeded", "completed"].some((v) => s.includes(v))) return "success"
  if (["failed", "error", "rejected"].some((v) => s.includes(v))) return "error"
  if (["warning", "review"].some((v) => s.includes(v))) return "warning"
  return "pending"
}

interface StatusBadgeProps {
  status: string
  variant?: Variant
  style?: CSSProperties
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    approved: "已批准",
    confirmed: "已确认",
    pending: "待处理",
    draft: "草稿",
    needs_review: "待审阅",
    completed: "已完成",
    failed: "失败",
    succeeded: "成功",
    rejected: "已拒绝",
    running: "运行中",
    queued: "排队中",
    "已绑定": "已绑定",
    "等待中": "等待中",
  }
  return map[status] ?? status
}

export function StatusBadge({ status, variant = "auto", style }: StatusBadgeProps) {
  const resolved = variant === "auto" ? inferVariant(status) : variant
  return (
    <span style={{ ...gateTheme.statusBadge, ...variantColors[resolved], ...style }}>
      {getStatusLabel(status)}
    </span>
  )
}
