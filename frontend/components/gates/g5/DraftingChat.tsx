"use client"

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react"

import {
  useDraftChatMessages,
  useSendDraftChatStream,
} from "../../../hooks/useSectionDraftChat"

type DraftingChatProps = Readonly<{
  systemId: string
  sectionKey: string
  onDraftReady?: (content: string) => void
}>

type LocalMessage = { role: "user" | "assistant"; content: string }

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  flex: 1,
  minHeight: 0,
}

const messagesStyle: CSSProperties = {
  flex: 1,
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
  padding: "8px",
  fontSize: "13px",
  lineHeight: 1.5,
}

const inputRowStyle: CSSProperties = {
  display: "flex",
  gap: "6px",
  padding: "6px 0",
}

const inputStyle: CSSProperties = {
  flex: 1,
  padding: "6px 10px",
  borderRadius: "6px",
  border: "1px solid rgba(148,163,184,0.2)",
  background: "rgba(15,23,42,0.6)",
  color: "#e2e8f0",
  fontSize: "13px",
  outline: "none",
}

const sendBtnStyle: CSSProperties = {
  padding: "6px 14px",
  borderRadius: "6px",
  border: "none",
  background: "#3b82f6",
  color: "#fff",
  fontSize: "13px",
  cursor: "pointer",
}

export function DraftingChat({ systemId, sectionKey, onDraftReady }: DraftingChatProps) {
  const { data: history } = useDraftChatMessages(systemId, sectionKey)
  const { send, streaming, streamContent, skillAssets, skillReview, skillRevisions } = useSendDraftChatStream(systemId, sectionKey)
  const [input, setInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)

  const messages: LocalMessage[] = [
    ...(history ?? []).map((m) => ({ role: m.role as "user" | "assistant", content: m.content })),
    ...(streaming ? [{ role: "assistant" as const, content: streamContent }] : []),
  ]

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [messages.length, streamContent])

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text || streaming) return
    setInput("")
    send(text)
  }, [input, streaming, send])

  const handleSave = useCallback(() => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant")
    if (lastAssistant && onDraftReady) onDraftReady(lastAssistant.content)
  }, [messages, onDraftReady])

  return (
    <div style={containerStyle}>
      <div ref={scrollRef} style={messagesStyle}>
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              background: m.role === "user" ? "rgba(59,130,246,0.15)" : "rgba(30,41,59,0.6)",
              padding: "6px 10px",
              borderRadius: "8px",
              maxWidth: "85%",
              whiteSpace: "pre-wrap",
            }}
          >
            {m.content || "..."}
          </div>
        ))}
      </div>
      {/* Skill structured output panels */}
      {(skillAssets.length > 0 || skillReview.length > 0 || skillRevisions.length > 0) && (
        <div style={{ padding: "6px 8px", fontSize: "12px", display: "flex", flexDirection: "column", gap: "4px" }}>
          {skillAssets.length > 0 && (
            <div style={{ background: "rgba(59,130,246,0.1)", borderRadius: "6px", padding: "6px 8px", border: "1px solid rgba(59,130,246,0.2)" }}>
              <span style={{ color: "#60a5fa", fontWeight: 600 }}>文献引入</span>
              {(skillAssets as Array<{ asset_type: string; payload: { title?: string; relevance?: string } }>).map((a, i) => (
                <div key={i} style={{ color: "#94a3b8", marginTop: "2px" }}>
                  {a.payload.title ?? "未知文献"} — {a.payload.relevance ?? ""}
                </div>
              ))}
            </div>
          )}
          {skillReview.length > 0 && (
            <div style={{ background: "rgba(234,179,8,0.1)", borderRadius: "6px", padding: "6px 8px", border: "1px solid rgba(234,179,8,0.2)" }}>
              <span style={{ color: "#facc15", fontWeight: 600 }}>评审评分</span>
              {(skillReview as Array<{ verdict?: string; dimensions?: Record<string, number> }>).map((r, i) => (
                <div key={i} style={{ color: "#94a3b8", marginTop: "2px" }}>
                  {r.verdict ?? "N/A"} | {r.dimensions ? Object.entries(r.dimensions).map(([k, v]) => `${k}: ${v}`).join(", ") : ""}
                </div>
              ))}
            </div>
          )}
          {skillRevisions.length > 0 && (
            <div style={{ background: "rgba(239,68,68,0.1)", borderRadius: "6px", padding: "6px 8px", border: "1px solid rgba(239,68,68,0.2)" }}>
              <span style={{ color: "#f87171", fontWeight: 600 }}>修订建议</span>
              {(skillRevisions as Array<{ severity?: string; issue?: string; suggestion?: string }>).map((r, i) => (
                <div key={i} style={{ color: "#94a3b8", marginTop: "2px" }}>
                  [{r.severity ?? "info"}] {r.issue ?? ""} → {r.suggestion ?? ""}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
      <div style={inputRowStyle}>
        <input
          style={inputStyle}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          placeholder={streaming ? "AI 正在生成..." : "输入写作指令..."}
          disabled={streaming}
        />
        <button style={sendBtnStyle} onClick={handleSend} disabled={streaming}>
          发送
        </button>
        {messages.some((m) => m.role === "assistant") && (
          <button
            style={{ ...sendBtnStyle, background: "#10b981" }}
            onClick={handleSave}
            disabled={streaming}
          >
            保存草稿
          </button>
        )}
      </div>
    </div>
  )
}
