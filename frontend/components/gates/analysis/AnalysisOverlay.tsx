"use client"

import { useCallback, useEffect, useState, type CSSProperties } from "react"

import type { ImageAnalysisItem } from "../../../hooks/useImageAnalyses"
import { usePatchFigurePlan } from "../../../hooks/useFigurePlan"
import { AnalysisChat } from "./AnalysisChat"
import { LiteraturePanel } from "./LiteraturePanel"

type AnalysisOverlayProps = Readonly<{
  systemId: string
  items: ImageAnalysisItem[]
  selectedIndex: number
  onChangeIndex: (index: number) => void
  onClose: () => void
}>

const backdropStyle: CSSProperties = {
  position: "fixed",
  top: 0, left: 0, right: 0, bottom: 0,
  background: "rgba(0, 0, 0, 0.55)",
  backdropFilter: "blur(6px)",
  WebkitBackdropFilter: "blur(6px)",
  zIndex: 1000,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}

const panelStyle: CSSProperties = {
  width: "90vw", maxWidth: "1200px", height: "85vh",
  borderRadius: "16px",
  border: "1px solid rgba(148, 163, 184, 0.15)",
  background: "rgba(15, 23, 42, 0.95)",
  boxShadow: "0 25px 50px rgba(0, 0, 0, 0.5)",
  display: "flex", flexDirection: "column", overflow: "hidden",
}

const headerStyle: CSSProperties = {
  display: "flex", justifyContent: "space-between", alignItems: "center",
  padding: "12px 20px",
  borderBottom: "1px solid rgba(148, 163, 184, 0.1)",
  flexShrink: 0,
}

const navBtnStyle: CSSProperties = {
  width: "28px", height: "28px", borderRadius: "6px",
  border: "1px solid rgba(148,163,184,0.15)",
  background: "transparent", color: "#94a3b8", fontSize: "14px",
  cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
}

const navBtnDisabled: CSSProperties = { ...navBtnStyle, opacity: 0.3, cursor: "not-allowed" }

const closeBtnStyle: CSSProperties = {
  width: "32px", height: "32px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.15)",
  background: "transparent", color: "#94a3b8", fontSize: "16px",
  cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
}

const bodyStyle: CSSProperties = {
  flex: 1, display: "flex", overflow: "hidden",
}

const leftPanelStyle: CSSProperties = {
  width: "40%", display: "flex", flexDirection: "column",
  borderRight: "1px solid rgba(148,163,184,0.1)",
  overflow: "auto", padding: "16px",
}

const rightPanelStyle: CSSProperties = {
  width: "60%", display: "flex", flexDirection: "column",
  overflow: "hidden", padding: "16px",
}

const imageContainerStyle: CSSProperties = {
  flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
  borderRadius: "8px", background: "rgba(0,0,0,0.3)",
  overflow: "hidden", minHeight: 0,
}

const metaCardStyle: CSSProperties = {
  marginTop: "12px", padding: "10px 12px", borderRadius: "8px",
  background: "rgba(15,23,42,0.5)", border: "1px solid rgba(148,163,184,0.1)",
  display: "flex", flexDirection: "column", gap: "4px", flexShrink: 0,
}

const metaLabelStyle: CSSProperties = { fontSize: "10px", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }
const metaValueStyle: CSSProperties = { fontSize: "12px", color: "#e2e8f0" }

export function AnalysisOverlay({ systemId, items, selectedIndex, onChangeIndex, onClose }: AnalysisOverlayProps) {
  const item = items[selectedIndex]
  const hasPrev = selectedIndex > 0
  const hasNext = selectedIndex < items.length - 1
  const firstAsset = item?.assets[0]

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") onClose()
    if (e.key === "ArrowLeft" && hasPrev) onChangeIndex(selectedIndex - 1)
    if (e.key === "ArrowRight" && hasNext) onChangeIndex(selectedIndex + 1)
  }, [onClose, hasPrev, hasNext, selectedIndex, onChangeIndex])

  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = "hidden"
    document.addEventListener("keydown", handleKeyDown)
    return () => {
      document.body.style.overflow = prev
      document.removeEventListener("keydown", handleKeyDown)
    }
  }, [handleKeyDown])

  if (!item) return null

  const isAnalyzed = !!item.latestAnalysis || !!item.evidenceText
  const statusBadge = isAnalyzed ? "已分析" : "待分析"
  const badgeColor = isAnalyzed ? "#4ade80" : "#fb923c"

  return (
    <div style={backdropStyle} onClick={onClose}>
      <div style={panelStyle} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={headerStyle}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button type="button" style={hasPrev ? navBtnStyle : navBtnDisabled}
              disabled={!hasPrev} onClick={() => hasPrev && onChangeIndex(selectedIndex - 1)}>←</button>
            <button type="button" style={hasNext ? navBtnStyle : navBtnDisabled}
              disabled={!hasNext} onClick={() => hasNext && onChangeIndex(selectedIndex + 1)}>→</button>
            <div style={{ fontSize: "14px", fontWeight: 700, color: "#f8fafc", marginLeft: "8px" }}>
              图片分析 — {item.figureNo} {item.title}
            </div>
            <span style={{ fontSize: "11px", fontWeight: 600, padding: "2px 8px", borderRadius: "6px",
              background: isAnalyzed ? "rgba(34,197,94,0.15)" : "rgba(251,146,60,0.15)",
              color: badgeColor, border: `1px solid ${isAnalyzed ? "rgba(34,197,94,0.2)" : "rgba(251,146,60,0.2)"}` }}>
              {statusBadge}
            </span>
          </div>
          <button type="button" onClick={onClose} style={closeBtnStyle} aria-label="关闭">✕</button>
        </div>

        {/* Body */}
        <div style={bodyStyle}>
          {/* Left: Image Preview */}
          <div style={leftPanelStyle}>
            <div style={imageContainerStyle}>
              {firstAsset?.previewUrl ? (
                <img
                  src={firstAsset.previewUrl}
                  alt={item.title}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/x-vibe-asset", JSON.stringify(firstAsset))
                  }}
                  style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain", cursor: "grab" }}
                />
              ) : (
                <div style={{ color: "#64748b", fontSize: "13px" }}>暂无图片预览</div>
              )}
            </div>
            <div style={metaCardStyle}>
              <div><span style={metaLabelStyle}>Figure</span> <span style={metaValueStyle}>{item.figureNo}</span></div>
              <div><span style={metaLabelStyle}>标题</span> <span style={metaValueStyle}>{item.title}</span></div>
              <div><span style={metaLabelStyle}>章节</span> <span style={metaValueStyle}>{item.sectionKey ?? "未关联"}</span></div>
              <div><span style={metaLabelStyle}>图片数</span> <span style={metaValueStyle}>{item.assets.length}</span></div>
              {item.latestAnalysis?.confidence != null ? (
                <div><span style={metaLabelStyle}>置信度</span> <span style={metaValueStyle}>{(item.latestAnalysis.confidence * 100).toFixed(0)}%</span></div>
              ) : null}
            </div>
          </div>

          {/* Right: Data Question + Analysis Chat + Evidence Text */}
          <div style={rightPanelStyle}>
            {item.dataQuestion ? (
              <div style={{ flexShrink: 0, marginBottom: "10px", padding: "8px 10px", borderRadius: "8px",
                background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.15)" }}>
                <div style={{ fontSize: "10px", color: "#fbbf24", fontWeight: 600, marginBottom: "3px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  数据问题（来自骨架）
                </div>
                <div style={{ fontSize: "12px", color: "#fde68a", lineHeight: 1.5 }}>{item.dataQuestion}</div>
              </div>
            ) : null}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
              <AnalysisChat planId={item.figurePlanId} />
            </div>
            <EvidenceTextEditor
              key={item.figurePlanId}
              systemId={systemId}
              planId={item.figurePlanId}
              initialText={item.evidenceText}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

const evidenceSectionStyle: CSSProperties = {
  flexShrink: 0, borderTop: "1px solid rgba(148,163,184,0.1)",
  paddingTop: "10px", marginTop: "10px",
}

const evidenceLabelStyle: CSSProperties = {
  fontSize: "10px", color: "#94a3b8", fontWeight: 600,
  textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "4px",
}

const evidenceTextareaStyle: CSSProperties = {
  width: "100%", padding: "8px 10px", borderRadius: "8px",
  border: "1px solid rgba(148,163,184,0.16)", background: "rgba(15,23,42,0.6)",
  color: "#e2e8f0", fontSize: "12px", resize: "vertical",
  outline: "none", minHeight: "60px", maxHeight: "120px", lineHeight: 1.5,
}

const evidenceSaveBtnStyle: CSSProperties = {
  padding: "4px 12px", borderRadius: "6px", fontSize: "11px", fontWeight: 600,
  border: "1px solid rgba(74,222,128,0.4)", background: "rgba(22,101,52,0.15)",
  color: "#4ade80", cursor: "pointer",
}

function EvidenceTextEditor({ systemId, planId, initialText }: {
  systemId: string; planId: string; initialText: string | null
}) {
  const [text, setText] = useState(initialText ?? "")
  const [saved, setSaved] = useState(false)
  const patchMut = usePatchFigurePlan(systemId)

  const handleSave = () => {
    patchMut.mutate(
      { planId, input: { evidenceText: text.trim() || null } },
      { onSuccess: () => { setSaved(true); setTimeout(() => setSaved(false), 2000) } },
    )
  }

  return (
    <div style={evidenceSectionStyle}>
      <div style={evidenceLabelStyle}>分析结论</div>
      <textarea
        style={evidenceTextareaStyle}
        value={text}
        onChange={(e) => { setText(e.target.value); setSaved(false) }}
        placeholder="在此填写对图片数据的分析结论，将图片中的数据细节转述为自然语言..."
      />
      <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "6px", alignItems: "center" }}>
        {saved ? <span style={{ fontSize: "11px", color: "#4ade80" }}>已保存</span> : null}
        <button
          type="button"
          style={patchMut.isPending ? { ...evidenceSaveBtnStyle, opacity: 0.5, cursor: "not-allowed" } : evidenceSaveBtnStyle}
          disabled={patchMut.isPending}
          onClick={handleSave}
        >
          {patchMut.isPending ? "保存中..." : "保存结论"}
        </button>
      </div>
    </div>
  )
}
