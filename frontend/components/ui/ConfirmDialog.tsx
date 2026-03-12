"use client"

import { createPortal } from "react-dom"
import type { CSSProperties } from "react"

interface ConfirmDialogProps {
  isOpen: boolean
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void
  isPending?: boolean
  confirmLabel?: string
}

const overlayStyle: CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0, 0, 0, 0.6)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 1000,
}

const dialogStyle: CSSProperties = {
  background: "rgba(15, 23, 42, 0.95)",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  borderRadius: "16px",
  padding: "24px",
  maxWidth: "400px",
  width: "90%",
}

const titleStyle: CSSProperties = {
  fontSize: "16px",
  fontWeight: 700,
  color: "#f8fafc",
  marginBottom: "10px",
}

const messageStyle: CSSProperties = {
  fontSize: "13px",
  color: "#94a3b8",
  lineHeight: 1.6,
  marginBottom: "20px",
}

const actionsStyle: CSSProperties = {
  display: "flex",
  gap: "10px",
  justifyContent: "flex-end",
}

const cancelBtnStyle: CSSProperties = {
  padding: "8px 16px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.3)",
  background: "transparent",
  color: "#94a3b8",
  fontSize: "13px",
  cursor: "pointer",
}

const confirmBtnStyle: CSSProperties = {
  padding: "8px 16px",
  borderRadius: "10px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  color: "#fb923c",
  fontSize: "13px",
  fontWeight: 600,
  cursor: "pointer",
}

export function ConfirmDialog({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  isPending = false,
  confirmLabel = "确认",
}: ConfirmDialogProps) {
  if (!isOpen) return null

  return createPortal(
    <div style={overlayStyle} onClick={onCancel}>
      <div style={dialogStyle} onClick={(e) => e.stopPropagation()}>
        <div style={titleStyle}>{title}</div>
        <div style={messageStyle}>{message}</div>
        <div style={actionsStyle}>
          <button style={cancelBtnStyle} onClick={onCancel} disabled={isPending}>
            取消
          </button>
          <button
            style={{ ...confirmBtnStyle, opacity: isPending ? 0.5 : 1, cursor: isPending ? "not-allowed" : "pointer" }}
            onClick={onConfirm}
            disabled={isPending}
          >
            {isPending ? "..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
