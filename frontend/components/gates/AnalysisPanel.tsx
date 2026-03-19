"use client"

import { useState, type CSSProperties } from "react"

import type { WorkflowSnapshot, Blocker } from "../../hooks/useProjectStatus"
import { useImageAnalyses } from "../../hooks/useImageAnalyses"
import { gateTheme } from "../../styles/gate-theme"
import { SectionCard } from "../ui/SectionCard"
import { StatusBadge } from "../ui/StatusBadge"
import { GateTaskStatus } from "./GateTaskStatus"
import { AnalysisOverlay } from "./analysis/AnalysisOverlay"

export type GateContentPanelProps = Readonly<{
  snapshot: WorkflowSnapshot | null
  blockers: Blocker[]
  systemId: string
}>

const statsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, 1fr)",
  gap: "8px",
  marginBottom: "12px",
}

const statsCardStyle: CSSProperties = {
  padding: "10px 12px",
  borderRadius: "10px",
  background: "rgba(15, 23, 42, 0.5)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  textAlign: "center",
}

const statsLabelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  marginBottom: "2px",
}

const cardGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
  gap: "10px",
}

const imageCardStyle: CSSProperties = {
  borderRadius: "10px",
  border: "1px solid rgba(148, 163, 184, 0.12)",
  background: "rgba(15, 23, 42, 0.5)",
  overflow: "hidden",
  cursor: "pointer",
  transition: "border-color 0.15s",
}

const thumbContainerStyle: CSSProperties = {
  width: "100%",
  height: "100px",
  background: "rgba(0,0,0,0.3)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  overflow: "hidden",
}

const cardInfoStyle: CSSProperties = {
  padding: "8px 10px",
  display: "flex",
  flexDirection: "column",
  gap: "2px",
}

const cardTitleStyle: CSSProperties = {
  fontSize: "12px",
  fontWeight: 600,
  color: "#e2e8f0",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

const cardSubStyle: CSSProperties = {
  fontSize: "10px",
  color: "#94a3b8",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

const blockerListStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
  marginTop: "8px",
}

const blockerItemStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  border: "1px solid rgba(248, 113, 113, 0.2)",
  background: "rgba(127, 29, 29, 0.1)",
  fontSize: "12px",
  color: "#fca5a5",
}

export function AnalysisPanel({ systemId, snapshot, blockers }: GateContentPanelProps) {
  const currentState = snapshot?.currentState ?? null
  const { data, isLoading, error } = useImageAnalyses(systemId)
  const [overlayOpen, setOverlayOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)

  const items = data?.items ?? []

  function handleCardClick(index: number) {
    setSelectedIndex(index)
    setOverlayOpen(true)
  }

  return (
    <div style={gateTheme.panel}>
      <GateTaskStatus systemId={systemId} gateKey="G2" />
      <SectionCard
        title={
          <span>
            数据与分析
            {currentState ? <StatusBadge status={currentState} style={{ marginLeft: "8px" }} /> : null}
          </span>
        }
        description="对 G1 上传的图片进行深度分析。点击图片卡片打开分析工作区。"
      >
        {/* Stats */}
        {data ? (
          <div style={statsGridStyle}>
            <div style={statsCardStyle}>
              <div style={statsLabelStyle}>全部</div>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#e2e8f0" }}>{data.total}</div>
            </div>
            <div style={statsCardStyle}>
              <div style={statsLabelStyle}>已分析</div>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#4ade80" }}>{data.analyzed}</div>
            </div>
            <div style={statsCardStyle}>
              <div style={statsLabelStyle}>待分析</div>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#fb923c" }}>{data.pending}</div>
            </div>
          </div>
        ) : null}

        {/* Card Grid */}
        {isLoading ? (
          <div style={{ fontSize: "12px", color: "#64748b" }}>加载图片中...</div>
        ) : error ? (
          <div style={{ fontSize: "12px", color: "#f87171" }}>
            加载失败：{error instanceof Error ? error.message : "未知错误"}
          </div>
        ) : items.length === 0 ? (
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            暂无图片数据。请在 G1 阶段上传图片后进入分析。
          </div>
        ) : (
          <div style={cardGridStyle}>
            {items.map((item, idx) => {
              const firstAsset = item.assets[0]
              const isAnalyzed = !!item.latestAnalysis || !!item.evidenceText
              return (
                <div key={item.figurePlanId} style={imageCardStyle}
                  onClick={() => handleCardClick(idx)}
                  role="button" tabIndex={0}
                  onKeyDown={(e) => { if (e.key === "Enter") handleCardClick(idx) }}>
                  <div style={thumbContainerStyle}>
                    {firstAsset?.previewUrl ? (
                      <img src={firstAsset.previewUrl} alt={item.title}
                        style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "cover" }} />
                    ) : (
                      <div style={{ color: "#475569", fontSize: "11px" }}>无预览</div>
                    )}
                  </div>
                  <div style={cardInfoStyle}>
                    <div style={cardTitleStyle}>{item.figureNo}</div>
                    <div style={cardSubStyle}>{item.title}</div>
                    <span style={{
                      fontSize: "10px", fontWeight: 600, padding: "1px 6px", borderRadius: "4px",
                      alignSelf: "flex-start",
                      background: isAnalyzed ? "rgba(34,197,94,0.15)" : "rgba(251,146,60,0.15)",
                      color: isAnalyzed ? "#4ade80" : "#fb923c",
                      border: `1px solid ${isAnalyzed ? "rgba(34,197,94,0.2)" : "rgba(251,146,60,0.2)"}`,
                    }}>
                      {isAnalyzed ? "已分析" : "待分析"}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </SectionCard>

      {/* Blockers */}
      {blockers.length > 0 ? (
        <SectionCard title={<span style={{ fontSize: "13px", color: "#fca5a5" }}>阻塞项 ({blockers.length})</span>}>
          <div style={blockerListStyle}>
            {blockers.map((b, i) => (
              <div key={`${b.code}-${i}`} style={blockerItemStyle}>
                <strong>{b.code}</strong>: {b.message}
              </div>
            ))}
          </div>
        </SectionCard>
      ) : null}

      {/* Overlay */}
      {overlayOpen && items.length > 0 ? (
        <AnalysisOverlay
          systemId={systemId}
          items={items}
          selectedIndex={selectedIndex}
          onChangeIndex={setSelectedIndex}
          onClose={() => setOverlayOpen(false)}
        />
      ) : null}
    </div>
  )
}
