"use client"

import type { CSSProperties } from "react"

import { useImageAnalyses, type ImageAnalysisItem } from "../../hooks/useImageAnalyses"

export type G2EvidencePanelProps = Readonly<{
  systemId: string
}>

function getAnalysisStatus(item: ImageAnalysisItem): "analyzed" | "pending" {
  return item.latestAnalysis ? "analyzed" : "pending"
}

const containerStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "12px",
}

const titleStyle: CSSProperties = {
  fontSize: "14px",
  fontWeight: 700,
  color: "#f8fafc",
}

const statsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(3, 1fr)",
  gap: "8px",
}

const statsCardStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.5)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
  textAlign: "center",
}

const statsLabelStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  marginBottom: "2px",
}

const readyBannerStyle: CSSProperties = {
  padding: "8px 12px",
  borderRadius: "8px",
  background: "rgba(34, 197, 94, 0.1)",
  border: "1px solid rgba(34, 197, 94, 0.2)",
  fontSize: "13px",
  color: "#4ade80",
  textAlign: "center",
}

const listStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "6px",
}

const itemStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "8px 12px",
  borderRadius: "8px",
  background: "rgba(15, 23, 42, 0.5)",
  border: "1px solid rgba(148, 163, 184, 0.1)",
}

const itemInfoStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "2px",
  flex: 1,
  minWidth: 0,
}

const itemTitleStyle: CSSProperties = {
  fontSize: "13px",
  fontWeight: 600,
  color: "#e2e8f0",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

const itemDescStyle: CSSProperties = {
  fontSize: "11px",
  color: "#94a3b8",
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
}

export function G2EvidencePanel({ systemId }: G2EvidencePanelProps) {
  const { data, isLoading, error } = useImageAnalyses(systemId)

  if (isLoading) {
    return <div style={{ fontSize: "12px", color: "#64748b" }}>加载分析进度中...</div>
  }

  if (error) {
    return (
      <div style={{ fontSize: "12px", color: "#f87171" }}>
        加载失败：{error instanceof Error ? error.message : "未知错误"}
      </div>
    )
  }

  const response = data
  if (!response || response.total === 0) {
    return (
      <div style={{ fontSize: "12px", color: "#64748b" }}>
        暂无图片数据，请在 G1 阶段上传图片后进入分析。
      </div>
    )
  }

  const allAnalyzed = response.pending === 0

  return (
    <div style={containerStyle}>
      <div style={titleStyle}>图片分析进度</div>

      <div style={statsGridStyle}>
        <div style={statsCardStyle}>
          <div style={statsLabelStyle}>全部</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#e2e8f0" }}>
            {response.total}
          </div>
        </div>
        <div style={statsCardStyle}>
          <div style={statsLabelStyle}>已分析</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#4ade80" }}>
            {response.analyzed}
          </div>
        </div>
        <div style={statsCardStyle}>
          <div style={statsLabelStyle}>待分析</div>
          <div style={{ fontSize: "18px", fontWeight: 700, color: "#fb923c" }}>
            {response.pending}
          </div>
        </div>
      </div>

      {allAnalyzed ? (
        <div style={readyBannerStyle}>
          所有图片分析已完成，可推进至 G3
        </div>
      ) : null}

      <div style={listStyle}>
        {response.items.map((item) => {
          const status = getAnalysisStatus(item)
          const isAnalyzed = status === "analyzed"
          return (
            <div key={item.figurePlanId} style={itemStyle}>
              <div style={itemInfoStyle}>
                <div style={itemTitleStyle}>
                  {item.figureNo}: {item.title}
                </div>
                <div style={itemDescStyle}>
                  {item.sectionKey ?? "未关联章节"} · {item.assets.length} 张图片
                  {item.latestAnalysis?.summary ? ` · ${item.latestAnalysis.summary}` : ""}
                </div>
              </div>
              <div
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "2px 8px",
                  borderRadius: "6px",
                  background: isAnalyzed
                    ? "rgba(34, 197, 94, 0.15)"
                    : "rgba(251, 146, 60, 0.15)",
                  color: isAnalyzed ? "#4ade80" : "#fb923c",
                  border: `1px solid ${isAnalyzed ? "rgba(34, 197, 94, 0.2)" : "rgba(251, 146, 60, 0.2)"}`,
                  flexShrink: 0,
                }}
              >
                {isAnalyzed ? "已分析" : "待分析"}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
