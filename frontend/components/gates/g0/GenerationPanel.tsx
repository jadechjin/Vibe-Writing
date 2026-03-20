"use client"

import { useState, useEffect, useRef, type CSSProperties } from "react"
import { useQueryClient } from "@tanstack/react-query"
import {
  useGenerateSkeleton,
  useSkeletons,
  useBuildPrompt,
} from "../../../hooks/useSkeletons"
import { apiRequest } from "../../../lib/api"
import { useWebSocket } from "../../../hooks/useWebSocket"

type GenerationPanelProps = {
  systemId: string
  onComplete: () => void
  onCancel: () => void
}

type Provider = "claude" | "codex" | "gemini"
type Step = "setup" | "prompt" | "running" | "result" | "error"

// ---- Styles ----

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "16px",
  padding: "20px",
  height: "100%",
}

const titleStyle: CSSProperties = {
  fontSize: "18px",
  fontWeight: 700,
  color: "#f8fafc",
  textAlign: "center",
  marginBottom: "4px",
}

const subtitleStyle: CSSProperties = {
  fontSize: "13px",
  color: "#94a3b8",
  textAlign: "center",
}

const providerRowStyle: CSSProperties = {
  display: "flex",
  gap: "12px",
  justifyContent: "center",
}

const cardBaseStyle: CSSProperties = {
  flex: 1,
  padding: "20px 12px",
  borderRadius: "12px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.5)",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: "8px",
  cursor: "pointer",
  transition: "all 0.2s ease",
}

const cardSelectedStyle: CSSProperties = {
  ...cardBaseStyle,
  borderColor: "rgba(249, 115, 22, 0.7)",
  boxShadow: "0 0 15px rgba(249, 115, 22, 0.2)",
  background: "rgba(154, 52, 18, 0.05)",
}

const iconStyle: CSSProperties = {
  width: "40px",
  height: "40px",
  borderRadius: "10px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "20px",
  fontWeight: 700,
  background: "rgba(148, 163, 184, 0.1)",
  color: "#e2e8f0",
}

const iconSelectedStyle: CSSProperties = {
  ...iconStyle,
  background: "rgba(249, 115, 22, 0.2)",
  color: "#fb923c",
}

const providerLabelStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 600,
  color: "#f8fafc",
}

const providerDescStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  textAlign: "center",
}

const footerStyle: CSSProperties = {
  display: "flex",
  gap: "12px",
  justifyContent: "center",
  marginTop: "auto",
}

const btnBase: CSSProperties = {
  padding: "10px 24px",
  borderRadius: "10px",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.15s",
}

const primaryBtnStyle: CSSProperties = {
  ...btnBase,
  border: "1px solid rgba(249, 115, 22, 0.5)",
  background: "rgba(154, 52, 18, 0.15)",
  color: "#fb923c",
}

const secondaryBtnStyle: CSSProperties = {
  ...btnBase,
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.3)",
  color: "#94a3b8",
}

const successBtnStyle: CSSProperties = {
  ...btnBase,
  border: "1px solid rgba(74, 222, 128, 0.5)",
  background: "rgba(22, 101, 52, 0.15)",
  color: "#4ade80",
}

const textareaStyle: CSSProperties = {
  width: "100%",
  minHeight: "300px",
  padding: "12px 14px",
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.2)",
  background: "rgba(15, 23, 42, 0.8)",
  color: "#e2e8f0",
  fontSize: "12px",
  fontFamily: "monospace",
  lineHeight: 1.6,
  resize: "vertical",
  outline: "none",
}

const resultContainer: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: "16px",
  flex: 1,
}

const resultIconStyle: CSSProperties = {
  width: "64px",
  height: "64px",
  borderRadius: "32px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  fontSize: "32px",
}

const successIconStyle: CSSProperties = {
  ...resultIconStyle,
  background: "rgba(34, 197, 94, 0.15)",
  color: "#22c55e",
  border: "2px solid rgba(34, 197, 94, 0.3)",
}

const errorIconStyle: CSSProperties = {
  ...resultIconStyle,
  background: "rgba(239, 68, 68, 0.15)",
  color: "#ef4444",
  border: "2px solid rgba(239, 68, 68, 0.3)",
}

const stepIndicatorStyle: CSSProperties = {
  display: "flex",
  gap: "8px",
  justifyContent: "center",
  marginBottom: "8px",
}

const stepDotBase: CSSProperties = {
  width: "8px",
  height: "8px",
  borderRadius: "50%",
  background: "#475569",
  transition: "all 0.2s",
}

const stepDotActive: CSSProperties = {
  ...stepDotBase,
  background: "#fb923c",
  boxShadow: "0 0 6px #fb923c",
}

const stepDotDone: CSSProperties = {
  ...stepDotBase,
  background: "#22c55e",
}

const spinnerStyle: CSSProperties = {
  width: "48px",
  height: "48px",
  border: "3px solid rgba(148, 163, 184, 0.15)",
  borderTopColor: "#fb923c",
  borderRadius: "50%",
  animation: "spin 0.8s linear infinite",
}

const STEPS: { key: Step; label: string }[] = [
  { key: "setup", label: "选择" },
  { key: "prompt", label: "提示词" },
  { key: "running", label: "生成" },
  { key: "result", label: "结果" },
]

export default function GenerationPanel({ systemId, onComplete, onCancel }: GenerationPanelProps) {
  const [step, setStep] = useState<Step>("setup")
  const [provider, setProvider] = useState<Provider>("claude")
  const [promptText, setPromptText] = useState("")
  const [elapsedTime, setElapsedTime] = useState(0)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [workflowId, setWorkflowId] = useState<string | null>(null)
  const [skeletonCountAtStart, setSkeletonCountAtStart] = useState<number | null>(null)
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null)

  const buildPromptMut = useBuildPrompt(systemId)
  const generateMut = useGenerateSkeleton(systemId)
  const queryClient = useQueryClient()
  const { data: skeletons } = useSkeletons(systemId)
  const { events } = useWebSocket({ systemId })

  function isEventFromCurrentRun(event: { timestamp: string }) {
    if (runStartedAt === null) return false
    const eventTime = Date.parse(event.timestamp)
    return Number.isFinite(eventTime) && eventTime >= runStartedAt
  }

  // 阶段 1 修复：WebSocket 事件回放
  // 处理事件先到、workflowId 后绑定的时序竞争问题
  useEffect(() => {
    if (step !== "running" || runStartedAt === null) return

    // 回放历史事件，查找是否已有完成事件
    // workflowId 未设置时，只接受本轮开始之后的同 system 事件
    const history = workflowId
      ? events.filter((e) => e.workflowId === workflowId && isEventFromCurrentRun(e))
      : events.filter((e) => isEventFromCurrentRun(e))

    const completed = history.find(
      (e) => e.type === "task.succeeded" && e.status === "succeeded"
    )

    if (completed) {
      console.log("[GenerationPanel] Found completed event in history, stopping timer")
      queryClient.invalidateQueries({ queryKey: ["skeletons", systemId] })
      setStep("result")
      return
    }

    const failed = history.find(
      (e) => e.type === "task.failed" && e.status === "failed"
    )

    if (failed) {
      console.log("[GenerationPanel] Found failed event in history")
      setErrorMessage(failed.message || "生成任务失败，请查看后端日志")
      setStep("error")
    }
  }, [workflowId, events, step, queryClient, systemId, runStartedAt])

  // Listen to WebSocket events for real-time updates
  useWebSocket({
    systemId,
    onInvalidate: (event) => {
      if (step !== "running" || runStartedAt === null) return

      console.log("[GenerationPanel] Received WebSocket event:", {
        type: event.type,
        status: event.status,
        workflowId: event.workflowId,
        currentWorkflowId: workflowId,
        message: event.message,
      })

      // 修复时序竞争：workflowId 可能还未设置（mutation onSuccess 尚未触发）
      // 当 workflowId 未设置时，也必须限定为“本轮开始之后”的事件
      const isMatch = (!workflowId || event.workflowId === workflowId) && isEventFromCurrentRun(event)

      if (isMatch) {
        if (event.type === "task.succeeded" && event.status === "succeeded") {
          console.log("[GenerationPanel] Skeleton generation succeeded, stopping timer")
          queryClient.invalidateQueries({ queryKey: ["skeletons", systemId] })
          setStep("result")
        } else if (event.type === "task.failed" && event.status === "failed") {
          console.log("[GenerationPanel] Skeleton generation failed:", event.message)
          setErrorMessage(event.message || "生成任务失败，请查看后端日志")
          setStep("error")
        }
      }
    },
  })

  // Load last provider choice
  useEffect(() => {
    const last = localStorage.getItem("skeleton-provider")
    if (last === "claude" || last === "codex" || last === "gemini") {
      setProvider(last as Provider)
    }
  }, [])

  // 阶段 1 修复：轮询兜底机制
  // 处理 WebSocket 丢包或连接问题，确保前端能可靠检测到完成状态
  useEffect(() => {
    if (step !== "running") return

    const timer = setInterval(() => {
      // 轮询 skeletons 列表，检查是否有新骨架生成
      queryClient.invalidateQueries({ queryKey: ["skeletons", systemId] })
    }, 2000)

    return () => clearInterval(timer)
  }, [step, queryClient, systemId])

  // 检测 skeletons 数据变化，判断是否生成完成
  useEffect(() => {
    if (step !== "running" || !skeletons || skeletonCountAtStart === null) return

    // 对比生成前后的数量变化，而非仅检查最后一个 skeleton 的 status
    if (skeletons.length > skeletonCountAtStart) {
      console.log("[GenerationPanel] Detected new skeleton via polling (count %d -> %d), stopping timer", skeletonCountAtStart, skeletons.length)
      setStep("result")
    }
  }, [skeletons, step, skeletonCountAtStart])

  // Timer for running step
  useEffect(() => {
    if (step !== "running") return
    const timer = setInterval(() => setElapsedTime((p) => p + 1), 1000)
    return () => clearInterval(timer)
  }, [step])

  function handleBuildPrompt() {
    localStorage.setItem("skeleton-provider", provider)
    buildPromptMut.mutate(
      { provider },
      {
        onSuccess: (data) => {
          setPromptText(data.prompt)
          setStep("prompt")
        },
        onError: (err) => {
          setErrorMessage(err instanceof Error ? err.message : "构建提示词失败")
          setStep("error")
        },
      }
    )
  }

  function handleConfirmPrompt() {
    const startedAt = Date.now()
    setSkeletonCountAtStart(skeletons?.length ?? 0)
    setRunStartedAt(startedAt)
    setStep("running")
    setElapsedTime(0)

    generateMut.mutate(
      { provider, customPrompt: promptText },
      {
        onSuccess: (data) => {
          const handle = (data as Record<string, unknown>).handle as Record<string, unknown> | undefined
          if (handle?.workflow_id) {
            setWorkflowId(handle.workflow_id as string)
          }
        },
        onError: (err) => {
          setErrorMessage(err instanceof Error ? err.message : "生成失败")
          setStep("error")
        },
      }
    )
  }

  function handleRetry() {
    setStep("setup")
    setErrorMessage(null)
    setPromptText("")
    setWorkflowId(null)
    setSkeletonCountAtStart(null)
    setRunStartedAt(null)
    setElapsedTime(0)
  }

  const stepIdx = STEPS.findIndex((s) => s.key === step)

  return (
    <div style={containerStyle}>
      {/* Step indicator */}
      <div style={stepIndicatorStyle}>
        {STEPS.map((s, i) => (
          <div
            key={s.key}
            style={i < stepIdx ? stepDotDone : i === stepIdx ? stepDotActive : stepDotBase}
            title={s.label}
          />
        ))}
      </div>

      {/* Step: Setup */}
      {step === "setup" && (
        <>
          <div style={titleStyle}>AI 生成骨架</div>
          <div style={subtitleStyle}>选择 AI 提供商，构建提示词后可审阅编辑</div>

          <div style={providerRowStyle}>
            {(["claude", "codex", "gemini"] as Provider[]).map((p) => (
              <div
                key={p}
                style={provider === p ? cardSelectedStyle : cardBaseStyle}
                onClick={() => setProvider(p)}
              >
                <div style={provider === p ? iconSelectedStyle : iconStyle}>
                  {p === "claude" ? "C" : p === "codex" ? "X" : "G"}
                </div>
                <div style={providerLabelStyle}>
                  {p === "claude" ? "Claude Code" : p === "codex" ? "Codex" : "Gemini"}
                </div>
                <div style={providerDescStyle}>
                  {p === "claude" ? "通用能力强" : p === "codex" ? "逻辑推理强" : "创意能力强"}
                </div>
              </div>
            ))}
          </div>

          <div style={footerStyle}>
            <button type="button" style={secondaryBtnStyle} onClick={onCancel}>取消</button>
            <button
              type="button"
              style={buildPromptMut.isPending ? { ...primaryBtnStyle, opacity: 0.5 } : primaryBtnStyle}
              onClick={handleBuildPrompt}
              disabled={buildPromptMut.isPending}
            >
              {buildPromptMut.isPending ? "构建中..." : "构建提示词"}
            </button>
          </div>
        </>
      )}

      {/* Step: Prompt editing */}
      {step === "prompt" && (
        <>
          <div style={titleStyle}>审阅提示词</div>
          <div style={subtitleStyle}>
            确认或编辑后发送给 {provider === "claude" ? "Claude Code" : provider === "codex" ? "Codex" : "Gemini"}
          </div>

          <textarea
            style={textareaStyle}
            value={promptText}
            onChange={(e) => setPromptText(e.target.value)}
            spellCheck={false}
          />

          <div style={footerStyle}>
            <button type="button" style={secondaryBtnStyle} onClick={() => setStep("setup")}>
              返回
            </button>
            <button type="button" style={primaryBtnStyle} onClick={handleConfirmPrompt}>
              确认并生成
            </button>
          </div>
        </>
      )}

      {/* Step: Running */}
      {step === "running" && (
        <>
          <div style={titleStyle}>
            {provider === "claude" ? "Claude Code" : provider === "codex" ? "Codex" : "Gemini"} 生成中
          </div>
          <div style={subtitleStyle}>
            系统终端已弹出，请在终端窗口中查看实时进度
          </div>

          <div style={resultContainer}>
            <div style={spinnerStyle} />
            <div style={{ fontSize: "14px", color: "#94a3b8" }}>
              已耗时 {elapsedTime} 秒
            </div>
          </div>

          <div style={footerStyle}>
            <button type="button" style={secondaryBtnStyle} onClick={onCancel}>取消</button>
          </div>
        </>
      )}

      {/* Step: Result (success) */}
      {step === "result" && (
        <div style={resultContainer}>
          <div style={successIconStyle}>✓</div>
          <div style={{ ...titleStyle, marginBottom: 0 }}>骨架生成成功</div>
          <div style={subtitleStyle}>可在骨架列表中查看和编辑结果</div>
          <div style={footerStyle}>
            <button type="button" style={successBtnStyle} onClick={onComplete}>查看骨架</button>
          </div>
        </div>
      )}

      {/* Step: Error */}
      {step === "error" && (
        <div style={resultContainer}>
          <div style={errorIconStyle}>✕</div>
          <div style={{ ...titleStyle, marginBottom: 0, color: "#ef4444" }}>操作失败</div>
          <div style={{ fontSize: "14px", color: "#94a3b8" }}>{errorMessage}</div>
          <div style={footerStyle}>
            <button type="button" style={secondaryBtnStyle} onClick={onCancel}>取消</button>
            <button type="button" style={primaryBtnStyle} onClick={handleRetry}>重试</button>
          </div>
        </div>
      )}

      <style jsx>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  )
}
