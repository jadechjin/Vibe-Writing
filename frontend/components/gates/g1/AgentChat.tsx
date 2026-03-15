"use client"

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react"

import {
  useChatMessages,
  sendChatMessageStream,
  type ChatMessageDetail,
} from "../../../hooks/useFigurePlanAssets"
import { useQueryClient } from "@tanstack/react-query"

type AgentChatProps = Readonly<{
  planId: string
}>

const PROVIDERS = [
  { key: "claude", label: "Claude" },
  { key: "codex", label: "Codex" },
  { key: "gemini", label: "Gemini" },
] as const

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  height: "400px",
}

const labelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  fontWeight: 600,
}

const tabBarStyle: CSSProperties = {
  display: "flex",
  gap: "4px",
}

const tabBase: CSSProperties = {
  padding: "4px 10px",
  borderRadius: "6px",
  border: "1px solid rgba(148,163,184,0.15)",
  background: "transparent",
  color: "#94a3b8",
  fontSize: "11px",
  fontWeight: 600,
  cursor: "pointer",
}

const tabActive: CSSProperties = {
  ...tabBase,
  borderColor: "rgba(251,146,60,0.5)",
  color: "#fb923c",
  background: "rgba(249,115,22,0.08)",
}

const messagesAreaStyle: CSSProperties = {
  flex: 1,
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  padding: "8px",
  borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.08)",
  background: "rgba(15,23,42,0.4)",
}

const userMsgStyle: CSSProperties = {
  alignSelf: "flex-end",
  maxWidth: "85%",
  padding: "6px 10px",
  borderRadius: "8px 8px 2px 8px",
  background: "rgba(30,41,59,0.8)",
  border: "1px solid rgba(251,146,60,0.2)",
  fontSize: "12px",
  color: "#e2e8f0",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
}

const assistantMsgStyle: CSSProperties = {
  alignSelf: "flex-start",
  maxWidth: "85%",
  padding: "6px 10px",
  borderRadius: "8px 8px 8px 2px",
  background: "rgba(15,23,42,0.5)",
  border: "1px solid rgba(148,163,184,0.1)",
  fontSize: "12px",
  color: "#e2e8f0",
  whiteSpace: "pre-wrap",
  wordBreak: "break-word",
}

const inputRowStyle: CSSProperties = {
  display: "flex",
  gap: "6px",
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

const sendBtnBase: CSSProperties = {
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

const sendBtnDisabled: CSSProperties = {
  ...sendBtnBase,
  opacity: 0.5,
  cursor: "not-allowed",
}

const thinkingStyle: CSSProperties = {
  ...assistantMsgStyle,
  color: "#64748b",
  fontStyle: "italic",
}

const emptyStyle: CSSProperties = {
  fontSize: "11px",
  color: "#475569",
  textAlign: "center",
  padding: "20px 0",
}

const errorStyle: CSSProperties = {
  fontSize: "11px",
  color: "#fca5a5",
  marginTop: "4px",
}

type LocalMessage = {
  role: "user" | "assistant"
  content: string
}

export function AgentChat({ planId }: AgentChatProps) {
  const [provider, setProvider] = useState<string>("claude")
  const [input, setInput] = useState("")
  const [isSending, setIsSending] = useState(false)
  const [streamingText, setStreamingText] = useState("")
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([])
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const queryClient = useQueryClient()

  const { data: serverMessages } = useChatMessages(planId, provider)

  // Merge server messages with local streaming state
  const displayMessages: LocalMessage[] = [
    ...(serverMessages ?? []).map((m) => ({ role: m.role as "user" | "assistant", content: m.content })),
    ...localMessages,
  ]

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [displayMessages.length, streamingText])

  // Reset local state when switching provider and abort ongoing request
  useEffect(() => {
    setLocalMessages([])
    setStreamingText("")
    setError(null)

    return () => {
      abortRef.current?.abort()
    }
  }, [provider])

  const handleSend = useCallback(async () => {
    const text = input.trim()
    if (!text || isSending) return

    setInput("")
    setError(null)
    setIsSending(true)
    setLocalMessages((prev) => [...prev, { role: "user", content: text }])
    setStreamingText("")

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await sendChatMessageStream(planId, provider, text, {
        onDelta: (chunk) => {
          setStreamingText((prev) => prev + chunk)
        },
        onDone: () => {
          // cleanup handled in finally block
        },
        onError: (err) => {
          setError(err)
        },
      }, controller.signal)
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") {
        setError(err.message)
      }
    } finally {
      setIsSending(false)
      abortRef.current = null
      setLocalMessages([])
      setStreamingText("")
      queryClient.invalidateQueries({ queryKey: ["figure-plan-chat", planId, provider] })
    }
  }, [input, isSending, planId, provider, queryClient])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  return (
    <div style={containerStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={labelStyle}>AI 讨论</div>
        <div style={tabBarStyle}>
          {PROVIDERS.map((p) => (
            <button
              key={p.key}
              type="button"
              style={provider === p.key ? tabActive : tabBase}
              onClick={() => setProvider(p.key)}
              disabled={isSending}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <div style={messagesAreaStyle}>
        {displayMessages.length === 0 && !streamingText ? (
          <div style={emptyStyle}>选择 Agent 开始讨论图表规划</div>
        ) : (
          <>
            {displayMessages.map((msg, i) => (
              <div key={i} style={msg.role === "user" ? userMsgStyle : assistantMsgStyle}>
                {msg.content}
              </div>
            ))}
            {streamingText ? (
              <div style={assistantMsgStyle}>{streamingText}</div>
            ) : null}
            {isSending && !streamingText ? (
              <div style={thinkingStyle}>思考中...</div>
            ) : null}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <div style={inputRowStyle}>
        <textarea
          style={textareaStyle}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息... (Ctrl+Enter 发送)"
          disabled={isSending}
          rows={1}
        />
        <button
          type="button"
          style={isSending ? sendBtnDisabled : sendBtnBase}
          disabled={isSending || !input.trim()}
          onClick={handleSend}
        >
          {isSending ? "..." : "发送"}
        </button>
      </div>
    </div>
  )
}
