"use client"

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react"

import {
  useChatMessages,
  useFigurePlanAssets,
  sendChatMessageStream,
} from "../../../hooks/useFigurePlanAssets"
import { useQueryClient } from "@tanstack/react-query"

type AnalysisChatProps = Readonly<{
  planId: string
  onAnalysisComplete?: () => void
}>

type LocalMessage = { role: "user" | "assistant"; content: string }

type PendingImage = {
  id: string
  file: File
  blobUrl: string
  localPath: string | null
  uploading: boolean
  error: string | null
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api"

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

const dropActiveStyle: CSSProperties = {
  outline: "2px dashed rgba(249,115,22,0.5)",
  outlineOffset: "-2px",
  background: "rgba(249,115,22,0.04)",
}

const thumbStripStyle: CSSProperties = {
  display: "flex",
  gap: "6px",
  overflowX: "auto",
  padding: "4px 0",
}

const thumbWrapStyle: CSSProperties = {
  position: "relative",
  width: "48px",
  height: "48px",
  borderRadius: "6px",
  overflow: "hidden",
  border: "1px solid rgba(148,163,184,0.15)",
  flexShrink: 0,
}

const thumbRemoveBtn: CSSProperties = {
  position: "absolute",
  top: "1px",
  right: "1px",
  width: "14px",
  height: "14px",
  borderRadius: "50%",
  background: "rgba(0,0,0,0.6)",
  color: "#fff",
  fontSize: "9px",
  border: "none",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}

let _imgIdCounter = 0
function nextImgId(): string {
  return `img-${++_imgIdCounter}-${Date.now()}`
}

async function uploadChatImage(
  planId: string,
  file: File,
): Promise<{ localPath: string; previewUrl: string | null }> {
  const formData = new FormData()
  formData.append("file", file)
  const res = await fetch(
    `${API_BASE_URL}/figure-plans/${planId}/chat/upload-image`,
    { method: "POST", body: formData },
  )
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  const json = await res.json()
  return {
    localPath: json.data?.localPath ?? json.data?.local_path ?? "",
    previewUrl: json.data?.previewUrl ?? json.data?.preview_url ?? null,
  }
}

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
  const [isDragOver, setIsDragOver] = useState(false)
  const [pendingImages, setPendingImages] = useState<PendingImage[]>([])
  const messagesAreaRef = useRef<HTMLDivElement>(null)
  const previousMessageCountRef = useRef(0)
  const abortRef = useRef<AbortController | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const queryClient = useQueryClient()

  const { data: planAssets } = useFigurePlanAssets(planId)
  const { data: serverMessages } = useChatMessages(planId, provider, "analysis")

  const libraryImageCount = planAssets?.length ?? 0
  const chatImageCount = pendingImages.filter((img) => img.localPath && !img.error).length
  const totalAccessibleImages = libraryImageCount + chatImageCount

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

  const addImages = useCallback((files: File[]) => {
    const imageFiles = files.filter((f) => f.type.startsWith("image/"))
    if (!imageFiles.length) return

    const newImages: PendingImage[] = imageFiles.map((file) => ({
      id: nextImgId(),
      file,
      blobUrl: URL.createObjectURL(file),
      localPath: null,
      uploading: true,
      error: null,
    }))
    setPendingImages((prev) => [...prev, ...newImages])

    for (const img of newImages) {
      uploadChatImage(planId, img.file)
        .then(({ localPath }) => {
          setPendingImages((prev) =>
            prev.map((p) => (p.id === img.id ? { ...p, localPath, uploading: false } : p)),
          )
        })
        .catch((err) => {
          setPendingImages((prev) =>
            prev.map((p) =>
              p.id === img.id ? { ...p, uploading: false, error: String(err) } : p,
            ),
          )
        })
    }
  }, [planId])

  const removeImage = useCallback((id: string) => {
    setPendingImages((prev) => {
      const img = prev.find((p) => p.id === id)
      if (img) URL.revokeObjectURL(img.blobUrl)
      return prev.filter((p) => p.id !== id)
    })
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)

    // Handle library asset drag (from FigurePlanUpload / AnalysisOverlay)
    const assetData = e.dataTransfer.getData("application/x-vibe-asset")
    if (assetData) {
      try {
        const asset = JSON.parse(assetData) as { previewUrl?: string; localPath?: string; fileName?: string }
        if (asset.previewUrl) {
          // Fetch the image from previewUrl and re-upload to get a local path
          fetch(asset.previewUrl)
            .then((res) => {
              if (!res.ok) throw new Error(`Fetch failed: ${res.status}`)
              return res.blob()
            })
            .then((blob) => {
              const file = new File([blob], asset.fileName || "image.png", { type: blob.type })
              addImages([file])
            })
            .catch(() => {
              // Fallback: still try to upload a placeholder so backend creates a local copy
              // Mark as error so user knows the drag didn't fully succeed
              const imgId = nextImgId()
              setPendingImages((prev) => [...prev, {
                id: imgId,
                file: new File([], asset.fileName || "image.png"),
                blobUrl: asset.previewUrl!,
                localPath: null,
                uploading: false,
                error: "图片预览链接已失效，请重新上传图片文件",
              }])
            })
          return
        }
      } catch { /* ignore parse errors */ }
    }

    const files = Array.from(e.dataTransfer.files)
    addImages(files)
  }, [addImages])

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    const files = Array.from(e.clipboardData.files)
    if (files.length) addImages(files)
  }, [addImages])

  const doSend = useCallback(async (text: string) => {
    if (!text.trim() || isSending) return

    // Inject uploaded image paths into message
    const uploadedPaths = pendingImages
      .filter((img) => img.localPath && !img.uploading)
      .map((img) => img.localPath!)
    let fullText = text.trim()
    if (uploadedPaths.length > 0) {
      fullText += `\n\n[附加图片路径：${uploadedPaths.join(", ")}]`
    }

    setInput("")
    setError(null)
    setIsSending(true)
    setLocalMessages((prev) => [...prev, { role: "user", content: fullText }])
    setStreamingText("")
    // Clear pending images after sending
    for (const img of pendingImages) URL.revokeObjectURL(img.blobUrl)
    setPendingImages([])

    const controller = new AbortController()
    abortRef.current = controller

    try {
      await sendChatMessageStream(planId, provider, fullText, {
        onDelta: (chunk) => setStreamingText((prev) => prev + chunk),
        onDone: () => { onAnalysisComplete?.() },
        onError: (err) => setError(err),
      }, controller.signal, "analysis")
    } catch (err) {
      if (err instanceof Error && err.name !== "AbortError") setError(err.message)
    } finally {
      setIsSending(false)
      abortRef.current = null
      setLocalMessages([])
      setStreamingText("")
      queryClient.invalidateQueries({ queryKey: ["figure-plan-chat", planId, provider, "analysis"] })
      queryClient.invalidateQueries({ queryKey: ["image-analyses"] })
    }
  }, [isSending, planId, provider, queryClient, onAnalysisComplete, pendingImages])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      doSend(input)
    }
  }, [doSend, input])

  const selectedProvider = PROVIDERS.find((p) => p.key === provider)

  return (
    <div
      style={{ ...containerStyle, ...(isDragOver ? dropActiveStyle : {}) }}
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
    >
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

      {totalAccessibleImages > 0 ? (
        <div style={{ fontSize: "10px", color: "#64748b", padding: "2px 8px" }}>
          AI 可访问 {libraryImageCount} 张素材图片{chatImageCount > 0 ? ` + ${chatImageCount} 张对话图片` : ""}
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

      {/* Image thumbnails */}
      {pendingImages.length > 0 ? (
        <div style={thumbStripStyle}>
          {pendingImages.map((img) => (
            <div key={img.id} style={thumbWrapStyle}>
              <img src={img.blobUrl} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              {img.uploading ? (
                <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.5)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "9px", color: "#fff" }}>...</div>
              ) : null}
              {img.error ? (
                <div style={{ position: "absolute", inset: 0, background: "rgba(127,29,29,0.7)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "8px", color: "#fca5a5" }}>失败</div>
              ) : null}
              <button type="button" style={thumbRemoveBtn} onClick={() => removeImage(img.id)}>✕</button>
            </div>
          ))}
        </div>
      ) : null}

      <input ref={fileInputRef} type="file" accept="image/*" multiple style={{ display: "none" }}
        onChange={(e) => { if (e.target.files) addImages(Array.from(e.target.files)); e.target.value = "" }} />

      <div style={inputRowStyle}>
        <button type="button" onClick={() => fileInputRef.current?.click()}
          style={{ ...btnBase, padding: "6px 8px", fontSize: "14px", lineHeight: 1, borderColor: "rgba(148,163,184,0.2)",
            background: "transparent", color: "#94a3b8" }}
          title="上传图片">📎</button>
        <textarea style={textareaStyle} value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown} onPaste={handlePaste}
          placeholder="输入问题或拖拽图片... (Ctrl+Enter 发送)" disabled={isSending} rows={1} />
        <button type="button" style={isSending || !input.trim() ? btnDisabled : btnBase}
          disabled={isSending || !input.trim()} onClick={() => doSend(input)}>
          {isSending ? "..." : "发送"}
        </button>
      </div>
    </div>
  )
}
