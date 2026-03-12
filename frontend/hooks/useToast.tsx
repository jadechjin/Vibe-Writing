"use client"

import { createContext, useCallback, useContext, useState, type CSSProperties, type ReactNode } from "react"

interface Toast {
  id: number
  message: string
  type: "success" | "error"
}

interface ToastContextValue {
  showSuccess: (message: string) => void
  showError: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let nextId = 0

const containerStyle: CSSProperties = {
  position: "fixed",
  bottom: "24px",
  right: "24px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  zIndex: 2000,
  pointerEvents: "none",
}

const toastBase: CSSProperties = {
  padding: "10px 16px",
  borderRadius: "10px",
  fontSize: "13px",
  fontWeight: 500,
  maxWidth: "320px",
  pointerEvents: "auto",
}

const successStyle: CSSProperties = {
  ...toastBase,
  background: "rgba(20, 83, 45, 0.9)",
  border: "1px solid rgba(34, 197, 94, 0.3)",
  color: "#4ade80",
}

const errorStyle: CSSProperties = {
  ...toastBase,
  background: "rgba(127, 29, 29, 0.9)",
  border: "1px solid rgba(239, 68, 68, 0.3)",
  color: "#f87171",
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message: string, type: Toast["type"]) => {
      const id = ++nextId
      setToasts((prev) => [...prev, { id, message, type }])
      setTimeout(() => dismiss(id), 4000)
    },
    [dismiss],
  )

  const showSuccess = useCallback((message: string) => push(message, "success"), [push])
  const showError = useCallback((message: string) => push(message, "error"), [push])

  return (
    <ToastContext.Provider value={{ showSuccess, showError }}>
      {children}
      <div style={containerStyle}>
        {toasts.map((t) => (
          <div key={t.id} style={t.type === "success" ? successStyle : errorStyle}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error("useToast must be used within ToastProvider")
  return ctx
}
