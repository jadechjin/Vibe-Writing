"use client"

import { useState, type CSSProperties } from "react"

import {
  useSkeletons,
  useGenerateSkeleton,
  useConfirmSkeleton,
} from "../../../hooks/useSkeletons"
import type { SkeletonSummary } from "../../../hooks/useSkeletons"

// ---- Props ----

export type SkeletonTabProps = Readonly<{
  systemId: string
  isReadOnly: boolean
}>

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "14px",
}

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
}

const titleStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 700,
  color: "#f8fafc",
}

const actionBarStyle: CSSProperties = {
  display: "flex",
  gap: "8px",
}

const btnStyle: CSSProperties = {
  padding: "6px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  fontSize: "12px",
  fontWeight: 600,
  color: "#fb923c",
  cursor: "pointer",
}

const btnDisabledStyle: CSSProperties = {
  ...btnStyle,
  opacity: 0.4,
  cursor: "not-allowed",
}

const confirmBtnStyle: CSSProperties = {
  ...btnStyle,
  border: "1px solid rgba(74, 222, 128, 0.5)",
  background: "rgba(22, 101, 52, 0.15)",
  color: "#4ade80",
}

const listStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
}

const itemStyle: CSSProperties = {
  padding: "12px 14px",
  borderRadius: "12px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.5)",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  cursor: "pointer",
}

const itemHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
}

const versionStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 700,
  color: "#e2e8f0",
}

const statusBadgeBase: CSSProperties = {
  fontSize: "11px",
  fontWeight: 600,
  padding: "2px 8px",
  borderRadius: "6px",
}

const emptyStyle: CSSProperties = {
  fontSize: "13px",
  color: "#64748b",
  textAlign: "center",
  padding: "24px 0",
}

const feedbackStyle: CSSProperties = {
  fontSize: "12px",
  padding: "6px 10px",
  borderRadius: "8px",
}

const previewStyle: CSSProperties = {
  fontSize: "12px",
  color: "#94a3b8",
  lineHeight: 1.5,
  padding: "8px 10px",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.7)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  maxHeight: "160px",
  overflow: "auto",
}

// ---- Helpers ----

function statusBadge(status: string): CSSProperties {
  if (status === "confirmed") {
    return { ...statusBadgeBase, color: "#4ade80", background: "rgba(22, 101, 52, 0.2)" }
  }
  return { ...statusBadgeBase, color: "#fbbf24", background: "rgba(120, 53, 15, 0.2)" }
}

// ---- Component ----

export function SkeletonTab({ systemId, isReadOnly }: SkeletonTabProps) {
  const { data: skeletons, isLoading } = useSkeletons(systemId)
  const generateMutation = useGenerateSkeleton(systemId)
  const confirmMutation = useConfirmSkeleton(systemId)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null)

  function handleGenerate() {
    generateMutation.mutate(
      {},
      {
        onSuccess: () => {
          setFeedback({ type: "success", msg: "骨架生成任务已提交" })
          setTimeout(() => setFeedback(null), 3000)
        },
        onError: () => {
          setFeedback({ type: "error", msg: "生成失败，请重试" })
          setTimeout(() => setFeedback(null), 5000)
        },
      },
    )
  }

  function handleConfirm(skeletonId: string) {
    confirmMutation.mutate(skeletonId, {
      onSuccess: () => {
        setFeedback({ type: "success", msg: "骨架已确认，章节结构已更新" })
        setTimeout(() => setFeedback(null), 3000)
      },
      onError: () => {
        setFeedback({ type: "error", msg: "确认失败，请重试" })
        setTimeout(() => setFeedback(null), 5000)
      },
    })
  }

  const canGenerate = !isReadOnly && !generateMutation.isPending
  const isBusy = generateMutation.isPending || confirmMutation.isPending

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <div style={titleStyle}>结构骨架 ({skeletons?.length ?? 0})</div>
        {!isReadOnly ? (
          <div style={actionBarStyle}>
            <button
              type="button"
              onClick={handleGenerate}
              disabled={!canGenerate}
              style={canGenerate ? btnStyle : btnDisabledStyle}
            >
              {generateMutation.isPending ? "生成中..." : "AI 生成"}
            </button>
          </div>
        ) : null}
      </div>

      {feedback ? (
        <div
          style={{
            ...feedbackStyle,
            color: feedback.type === "success" ? "#4ade80" : "#f87171",
            background: feedback.type === "success" ? "rgba(22, 101, 52, 0.15)" : "rgba(127, 29, 29, 0.15)",
          }}
        >
          {feedback.msg}
        </div>
      ) : null}

      {isLoading ? (
        <div style={emptyStyle}>加载中...</div>
      ) : !skeletons || skeletons.length === 0 ? (
        <div style={emptyStyle}>暂无结构骨架，点击「AI 生成」创建</div>
      ) : (
        <div style={listStyle}>
          {skeletons.map((sk: SkeletonSummary) => {
            const isExpanded = expandedId === sk.id
            const isDraft = sk.status === "draft"
            return (
              <div
                key={sk.id}
                style={itemStyle}
                onClick={() => setExpandedId(isExpanded ? null : sk.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") setExpandedId(isExpanded ? null : sk.id)
                }}
              >
                <div style={itemHeaderStyle}>
                  <div style={versionStyle}>
                    v{sk.version}
                    {sk.changeSummary ? ` — ${sk.changeSummary}` : ""}
                  </div>
                  <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                    <span style={statusBadge(sk.status)}>{sk.status}</span>
                    {isDraft && !isReadOnly ? (
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleConfirm(sk.id) }}
                        disabled={isBusy}
                        style={isBusy ? btnDisabledStyle : confirmBtnStyle}
                      >
                        确认
                      </button>
                    ) : null}
                  </div>
                </div>
                {isExpanded ? (
                  <div style={previewStyle}>
                    {sk.changeSummary ?? "无变更摘要"}
                    <br />
                    <span style={{ fontSize: "11px", color: "#64748b" }}>
                      创建于 {new Date(sk.createdAt).toLocaleString("zh-CN")}
                    </span>
                  </div>
                ) : null}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
