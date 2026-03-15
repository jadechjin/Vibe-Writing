"use client"

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react"

import {
  useChatMessages,
  sendChatMessageStream,
} from "../../../hooks/useFigurePlanAssets"
import { useQueryClient } from "@tanstack/react-query"

type AnalysisChatProps = Readonly<{
  planId: string
  onAnalysisComplete?: () => void
}>

type LocalMessage = { role: "user" | "assistant"; content: string }

const PROVIDERS = [
  { key: "claude", label: "Claude", degraded: false },
  { key: "gemini", label: "Gemini", degraded: false },
  { key: "codex", label: "Codex", degraded: true },
] as const

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  flex: 1,
  minHeight: 0,
}

const tabBarStyle: CSSProperties = { display: "flex", gap: "4px" }

const tabBase: CSSProperties = {
  padding: "3px 10px",
  borderRadius: "6px",
  border: "1px solid rgba(148,163,184,0.15)",
  background: "transparent",
  color: "#94a3b8",
  fontSize: "11px",
  cursor: "pointer",
}

const tabActive: CSSProperties = {
  ...tabBase,
  borderColor: "rgba(249,115,22,0.5)",
  background: "rgba(154,52,18,0.15)",
  color: "#fb923c",
}

const messagesAreaStyle: CSSProperties = {
  flex: 1,
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  padding: "8px",
  borderRadius: "8px",
  background: "rgba(15,23,42,0.4)",
  border: "1px solid rgba(148,163,184,0.08)",
  minHeight: 0,
}

const userMsgStyle: CSSProperties = {
  alignSelf: "flex-end",
  maxWidth: "80%",
  padding: "6px 10px",
  borderRadius: "10px 10px 2px 10px",
  background: "rgba(249,115,22,0.12)",
  border: "1px solid rgba(249,115,22,0.2)",
  fontSize: "12px",
  color: "#e2e8f0",
  lineHeight: 1.5,
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
}

const assistantMsgStyle: CSSProperties = {
  alignSelf: "flex-start",
  maxWidth: "85%",
  padding: "6px 10px",
  borderRadius: "10px 10px 10px 2px",
  background: "rgba(148,163,184,0.08)",
  border: "1px solid rgba(148,163,184,0.1)",
  fontSize: "12px",
  color: "#cbd5e1",
  lineHeight: 1.5,
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
}

const inputRowStyle: CSSProperties = {
  display: "flex",
  gap: "6px",
  alignItems: "flex-end",
}

const textareaStyle: CSSProperties = {
  flex: 1,
  padding: "8px 10px",
  borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.16)",
  background: "rgba(15,23,42,0.6)",
  color: "#e2e8f0",
  fontSize: "12px",
  resize: "none",
  outline: "none",
  minHeight: "36px",
  maxHeight: "80px",
  lineHeight: 1.4,
}

const btnBase: CSSProperties = {
  padding: "6px 14px",
  borderRadius: "8px",
  border: "1px solid rgba(249,115,22,0.5)",
  background: "rgba(154,52,18,0.15)",
  color: "#fb923c",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
  whiteSpace: "nowrap",
}

const btnDisabled: CSSProperties = { ...btnBase, opacity: 0.5, cursor: "not-allowed" }

const analyzeBtnStyle: CSSProperties = {
  ...btnBase,
  borderColor: "rgba(74,222,128,0.5)",
  background: "rgba(22,101,52,0.15)",
  color: "#4ade80",
}

const errorStyle: CSSProperties = { fontSize: "11px", color: "#f87171" }
const emptyStyle: CSSProperties = { fontSize: "12px", color: "#64748b", textAlign: "center", padding: "20px 0" }
const thinkingStyle: CSSProperties = { ...assistantMsgStyle, color: "#64748b", fontStyle: "italic" }

const AUTO_ANALYSIS_PROMPT = `请对这张图片进行深度分析：
1. 描述图片内容（图表类型、轴标签、数据趋势、关键数值）
2. 使用学术搜索工具查找相关文献
3. 使用知识库工具检索相关数据
4. 输出结构化分析结果（JSON 格式，包含中文摘要、文献引用、置信度评估）`

export function AnalysisChat({ planId, onAnalysisComplete }: AnalysisChatProps) {
  const [provider, setProvider] = useState<string>("claude")
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [streamingText, setStreamingText] = useState("")
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([])
  const [error, setError] = useState<string | null>(null)
  const messagesAreaRef = useRef<HTMLDivElement>(null)
  const previousMessageCountRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)
  const queryClient = useQueryClient()

  const { data: serverMessages } = useChatMessages(planId, provider)

  const displayMessages: LocalMessage[] = [
    ...(serverMessages ?? []).map((m) => ({ role: m.role as "user" | "assistant", content: m.content })),
    ...localMessages,
  ]

  const scrollMessagesToBottom = useCallback((behavior: ScrollBehavior) => {
    const container = messagesAreaRef.current
    if (!container) return
    container.scrollTo({ top: container.scrollHeight, behavior })
  }, [])

  useEffect(() => {
    if (displayMessages.length > previousMessageCountRef.current) {
      scrollMessagesToBottom("smooth")
    }
    previousMessageCountRef.current = displayMessages.length
  }, [displayMessages.length, scrollMessagesToBottom])

  useEffect(() => {
    if (!streamingText) return
    scrollMessagesToBottom("auto")
  }, [streamingText, scrollMessagesToBottom])

  useEffect(() => {
    setLocalMessages([])
    setStreamingText("")
    setError(null)
    return () => { abortRef.current?.abort() }
  }, [provider])

  const doSend = useCallback(async (text: string) => {
    if (!text.trim() || isSending) return
    setInput("")
    setError(null)
    setIsSending(true)
    setLocalMessages((prev) => [...prev, { role: "user", content: text.trim() }])
    setStreamingText("")

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await sendChatMessageStream(planId, provider, text.trim(), {
        onDelta: (chunk) => setStreamingText((prev) => prev + chunk),
        onDone: () => { onAnalysisComplete?.() },
        onError: (err) => setError(err),
      }, controller.signal)
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") setError(err.message)
    } finally {
      setIsSending(false)
      abortRef.current = null
      setLocalMessages([])
      setStreamingText("")
      queryClient.invalidateQueries({ queryKey: ["figure-plan-chat", planId, provider] })
      queryClient.invalidateQueries({ queryKey: ["image-analyses"] })
    }
  }, [isSending, planId, provider, queryClient, onAnalysisComplete])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      doSend(input)
    }
  }, [doSend, input])

  const selectedProvider = PROVIDERS.find((p) => p.key === provider)

  return (
    <div style={containerStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontSize: "11px", color: "#94a3b8", fontWeight: 600 }}>AI 分析</div>
        <div style={tabBarStyle}>
          {PROVIDERS.map((p) => (
            <button key={p.key} type="button" style={provider === p.key ? tabActive : tabBase}
              onClick={() => setProvider(p.key)} disabled={isSending}>
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {selectedProvider?.degraded ? (
        <div style={{ fontSize: "11px", color: "#fb923c", padding: "4px 8px", borderRadius: "6px",
          background: "rgba(251,146,60,0.08)", border: "1px solid rgba(251,146,60,0.15)" }}>
          Codex 不支持 MCP 工具调用，学术搜索和知识库检索功能将不可用。
        </div>
      ) : null}

      <div ref={messagesAreaRef} style={messagesAreaStyle}>
        {displayMessages.length === 0 && !streamingText ? (
          <div style={emptyStyle}>点击「自动分析」或输入问题开始</div>
        ) : (
          <>
            {displayMessages.map((msg, i) => (
              <div key={i} style={msg.role === "user" ? userMsgStyle : assistantMsgStyle}>
                {msg.content}
              </div>
            ))}
            {streamingText ? <div style={assistantMsgStyle}>{streamingText}</div> : null}
            {isSending && !streamingText ? <div style={thinkingStyle}>分析中...</div> : null}
          </>
        )}
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <div style={{ display: "flex", gap: "6px" }}>
        <button type="button" style={isSending ? { ...analyzeBtnStyle, ...btnDisabled } : analyzeBtnStyle}
          disabled={isSending} onClick={() => doSend(AUTO_ANALYSIS_PROMPT)}>
          自动分析
        </button>
      </div>

      <div style={inputRowStyle}>
        <textarea style={textareaStyle} value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown} placeholder="输入问题... (Ctrl+Enter 发送)" disabled={isSending} rows={1} />
        <button type="button" style={isSending || !input.trim() ? btnDisabled : btnBase}
          disabled={isSending || !input.trim()} onClick={() => doSend(input)}>
          {isSending ? "..." : "发送"}
        </button>
      </div>
    </div>
  )
}
